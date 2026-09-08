"""Bounded requests, one durable writer, and provider-independent recovery."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import threading
import time


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


@dataclass(frozen=True)
class Job:
    case: str
    model: str
    request: dict

    @property
    def key(self):
        return encode([self.case, self.model])


@dataclass
class Outcome:
    status: str  # success, flagged, retry, terminal, quota, blocked, uncertain
    value: dict = field(default_factory=dict)
    retry_after: float = 0


STATUSES = {"success", "flagged", "retry", "terminal", "quota", "blocked", "uncertain"}


@contextmanager
def graceful_interrupt(stop):
    # A SIGINT between fsync and the state update must not replay a saved event.
    # Calls must have bounded transport timeouts so draining finishes promptly.
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.signal(signal.SIGINT, lambda *_: stop.set())
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


@contextmanager
def writer_lock(folder):
    lock = folder / "writer.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError("Writer lock exists; verify the old process before recovery") from None
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        lock.unlink()


def append(path, event):
    # Encode before opening, so serialization failures do not damage the log.
    data = (encode(event) + "\n").encode("utf-8")
    with path.open("ab") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def replay(path, manifest):
    states = {key: {"status": "pending", "attempts": manifest.get("initial_attempts", {}).get(key, 0), "ready_at": 0, "value": {}}
              for key in manifest["jobs"]}
    if not path.exists():
        append(path, manifest)
        return states
    data = path.read_bytes()
    if not data.endswith(b"\n"):
        raise ValueError("Incomplete journal tail; preserve and review before recovery")
    records = [json.loads(line) for line in data.splitlines()]
    if not records or records[0] != manifest:
        raise ValueError("Run identity changed; refuse to reuse journal")
    for event in records[1:]:
        state = states[event["key"]]
        if event["type"] == "start":
            if state["status"] not in {"pending", "retry", "quota", "blocked"}:
                raise ValueError("Invalid start transition")
            if event["attempt"] != state["attempts"] + 1:
                raise ValueError("Invalid attempt sequence")
            state.update(status="uncertain", attempts=event["attempt"])
        elif event["type"] == "result":
            if state["status"] != "uncertain" or state["attempts"] != event["attempt"]:
                raise ValueError("Result without its request start")
            if event["status"] not in STATUSES:
                raise ValueError("Invalid outcome state")
            state.update(status=event["status"], value=event["value"], ready_at=event["ready_at"])
        else:
            raise ValueError("Unknown journal event")
    return states


def run(jobs, call, folder, *, concurrency=2, max_attempts=3, contract=None,
        stop=None, resume_blocked=False, checkpoint=None, initial_attempts=None):
    """call(job, attempt) makes ONE bounded-time request, with SDK retries disabled.

    checkpoint is an optional coordinator callback after each durable result.
    Unknown exceptions are
    uncertain and stop new dispatches. Existing in-flight calls are drained.
    """
    if type(concurrency) is not int or concurrency < 1:
        raise ValueError("concurrency must be a positive integer")
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    # Copy inputs once to detach caller-owned mutable dictionaries.
    jobs = [Job(**json.loads(encode(asdict(job)))) for job in jobs]
    by_key = {job.key: job for job in jobs}
    if len(by_key) != len(jobs):
        raise ValueError("Duplicate case/model job")
    initial_attempts = initial_attempts or {}
    if any(k not in by_key or type(v) is not int or v < 0 for k, v in initial_attempts.items()):
        raise ValueError("Invalid inherited attempt counts")
    manifest = {"schema": 1, "max_attempts": max_attempts, "contract": contract,
                "initial_attempts": initial_attempts,
                "jobs": {job.key: hashlib.sha256(encode(asdict(job)).encode()).hexdigest()
                         for job in jobs}}
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    journal = folder / "events.jsonl"
    stop = stop or threading.Event()
    with graceful_interrupt(stop), writer_lock(folder):
        states = replay(journal, manifest)
        paused = any(s["status"] == "uncertain" or
                     (s["status"] in {"quota", "blocked"} and not resume_blocked)
                     for s in states.values())
        allowed = {"pending", "retry"} | ({"quota", "blocked"} if resume_blocked else set())
        pending = [key for key, state in states.items()
                   if state["status"] in allowed and state["attempts"] < max_attempts]
        active = {}
        calls = 0
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            while active or (pending and not paused and not stop.is_set()):
                try:
                    # Do not refill until all observed completions have been saved.
                    while pending and len(active) < concurrency and not paused and not stop.is_set():
                        now = time.time()
                        key = next((k for k in pending if states[k]["ready_at"] <= now), None)
                        if key is None:
                            break
                        pending.remove(key)
                        state = states[key]
                        attempt = state["attempts"] + 1
                        append(journal, {"type": "start", "key": key, "attempt": attempt})
                        state.update(status="uncertain", attempts=attempt)
                        # Workers get a private request; only the coordinator sees states.
                        job = Job(**json.loads(encode(asdict(by_key[key]))))
                        active[pool.submit(call, job, attempt)] = key
                        calls += 1
                    if not active:
                        if pending and not paused and not stop.is_set():
                            stop.wait(min(.05, max(0, min(states[k]["ready_at"] for k in pending) - time.time())))
                        continue
                    done, _ = wait(active, timeout=.05, return_when=FIRST_COMPLETED)
                    for future in done:
                        key = active[future]
                        state = states[key]
                        try:
                            outcome = future.result()
                            if not isinstance(outcome, Outcome) or outcome.status not in STATUSES:
                                raise ValueError("Invalid adapter result")
                            if not math.isfinite(outcome.retry_after) or outcome.retry_after < 0:
                                raise ValueError("Invalid retry delay")
                            encode(outcome.value)
                        except Exception as exc:
                            # Do not journal provider exception text: it may contain secrets.
                            outcome = Outcome("uncertain", {"error_type": type(exc).__name__})
                        if outcome.status == "retry" and state["attempts"] >= max_attempts:
                            outcome.status = "terminal"
                        ready_at = time.time() + outcome.retry_after
                        append(journal, {"type": "result", "key": key,
                                         "attempt": state["attempts"], "status": outcome.status,
                                         "value": outcome.value, "ready_at": ready_at})
                        state.update(status=outcome.status, value=outcome.value, ready_at=ready_at)
                        del active[future]
                        if outcome.status in {"quota", "blocked", "uncertain"}:
                            paused = True
                        elif outcome.status == "retry":
                            pending.append(key)
                        if checkpoint:
                            checkpoint(states)
                except KeyboardInterrupt:
                    # Stop dispatching, retain and save already submitted responses.
                    stop.set()
        return {"calls": calls, "states": states,
                "complete": all(s["status"] in {"success", "flagged", "terminal"}
                                for s in states.values()),
                "paused": paused or stop.is_set()}
