"""Durable concurrent collection for the existing Morning benchmark contracts."""
from collections import Counter, deque
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import urllib.request
import os
from pathlib import Path
import shutil
import threading
import time

import pandas as pd

import radle_job_queue as queue


def retry_delay(header, attempt, now=None):
    """Respect numeric and HTTP-date Retry-After; malformed values use backoff."""
    delay = max(60, min(300, 2 ** min(attempt, 8)))
    try:
        value = float(header)
    except (TypeError, ValueError):
        try:
            value = parsedate_to_datetime(header).timestamp() - (time.time() if now is None else now)
        except (TypeError, ValueError, OverflowError):
            return delay
    import math
    return max(delay, value) if math.isfinite(value) and value >= 0 else delay


def waiting_counts(states, active, max_attempts):
    active = set(active)
    pending = [s for k, s in states.items() if k not in active and s['status'] in {'pending', 'retry'}]
    return (sum(queue.has_attempt(s, max_attempts) for s in pending),
            sum(not queue.has_attempt(s, max_attempts) for s in pending))


def check_openrouter_funds(client):
    """Read billing metadata only; never persist credentials or raw API errors."""
    evidence = {'checked_utc': datetime.now(timezone.utc).isoformat(),
                'status': 'unknown'}
    try:
        if str(client.base_url).rstrip('/') != 'https://openrouter.ai/api/v1':
            return evidence
        data = {}
        for endpoint in ('key', 'credits'):
            request = urllib.request.Request(
                'https://openrouter.ai/api/v1/' + endpoint,
                headers={'Authorization': 'Bearer ' + client.api_key})
            with urllib.request.urlopen(request, timeout=15) as response:
                data[endpoint] = json.load(response)['data']
        key = data['key']
        account_remaining = float(data['credits']['total_credits']) - float(data['credits']['total_usage'])
        unlimited = key.get('limit') is None and key.get('limit_remaining') is None
        key_remaining = None if unlimited else float(key['limit_remaining'])
        if not math.isfinite(account_remaining) or (key_remaining is not None and not math.isfinite(key_remaining)):
            return evidence
        evidence.update(account_remaining=account_remaining,
                        key_remaining=key_remaining, key_unlimited=unlimited,
                        status='available' if account_remaining > 0 and
                        (unlimited or key_remaining > 0) else 'exhausted')
    except Exception:
        pass
    return evidence


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as handle:
        handle.write(queue.encode(value) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def diagnostic(exc):
    known = getattr(exc, "radle_diagnostic", None)
    if isinstance(known, dict):
        result = dict(known)
    else:
        known_messages = {
            "Responses stream ended without a completed response.": "Stream ended before a complete response arrived.",
            "Streamed reasoning differs from the final typed reasoning fields.": "Stream reasoning failed its consistency check.",
            "Reasoning stream delta/done mismatch.": "Stream fragments failed their consistency check.",
        }
        summary = known_messages.get(str(exc), "Request outcome could not be verified; inspect saved evidence.")
        status = getattr(exc, "status_code", None)
        if status == 429:
            summary = "Provider rate limit; retry will wait."
        elif status in {401, 403}:
            # Classify locally; do not print arbitrary provider text or echoed inputs.
            message = str(exc).lower()
            if any(term in message for term in ('limit exceeded', 'quota', 'balance', 'budget')):
                summary = "Provider reports a spending or quota limit."
            elif any(term in message for term in ('moderation', 'content policy', 'content filter', 'guardrail')):
                summary = "Provider rejected the request under its content or guardrail policy."
            elif 'allowlist' in message or 'ip address' in message:
                summary = "Provider reports an IP or access allowlist restriction."
            elif status == 401:
                summary = "Provider rejected authentication."
            else:
                summary = "Provider refused access (HTTP 403); exact cause is not established."
        elif status == 402:
            summary = "Insufficient provider credit."
        elif status in {500, 502, 503, 504}:
            summary = "Temporary provider server error."
        elif "Timeout" in type(exc).__name__:
            summary = "Request timed out; remote completion is unknown."
        result = {"summary": summary}
    result["error_type"] = type(exc).__name__
    if getattr(exc, "radle_archive", None):
        result["archive"] = str(exc.radle_archive)
    return result


def progress_summary(states, active, jobs_by_case, total_jobs, total_cases, repair_enabled=False, max_attempts=3):
    active = set(active)
    counts = Counter(v['status'] for k, v in states.items() if k not in active)
    collected = total_jobs - len(states) + counts['success'] + counts['flagged']
    cases_done = sum(not keys or all(states[k]['status'] in {'success', 'flagged'} for k in keys)
                     for keys in jobs_by_case.values())
    review = sum(counts[k] for k in ('uncertain', 'blocked', 'quota', 'terminal', 'rejected'))
    review_label = "awaiting repair" if repair_enabled else "need review"
    failed_label = f" | {counts['failed']} failed" if counts['failed'] else ""
    runnable, exhausted = waiting_counts(states, active, max_attempts)
    return (f"{collected}/{total_jobs} answers collected | {cases_done}/{total_cases} cases complete | "
            f"{len(active)} running | {counts['retry']} retry waiting | {review} {review_label} | {runnable} queued | {exhausted} exhausted{failed_label}")



def notebook_display():
    """Use the notebook publisher when available; ordinary consoles stay plain."""
    try:
        from IPython import get_ipython
        from IPython.display import display
        if getattr(get_ipython(), 'kernel', None) is not None:
            return display
    except Exception:
        pass
    return None


class LiveProgress:
    """Read-only view of coordinator state; rendering never controls collection."""
    zone = timezone(timedelta(hours=5, minutes=30), 'IST')

    def __init__(self, models, cases, jobs, jobs_by_case, concurrency, max_attempts, checkpoint_path):
        self.models, self.cases = models, cases
        self.active_models = {m["name"] for m in models}
        self.jobs_by_case = jobs_by_case
        self.by_model = {m['name']: [j.key for j in jobs if j.model == m['name']] for m in models}
        self.slots, self.max_attempts = concurrency, max_attempts
        self.publisher, self.handle = notebook_display(), None
        self.starts, self.events = {}, deque(maxlen=5)
        self.states, self.active = {}, ()
        self.phase, self.last_save, self.backup = 'RUNNING', None, 'None yet'
        self.repair_enabled = False
        try:
            record = json.loads(Path(checkpoint_path).read_text(encoding='utf-8'))
            self.backup = self.backup_label(record['numbered_backup'], record['saved_utc'])
        except (OSError, ValueError, KeyError, TypeError):
            pass

    @classmethod
    def stamp(cls):
        return datetime.now(cls.zone).strftime('%H:%M:%S')

    @classmethod
    def backup_label(cls, path, saved_utc):
        name = str(path).replace('\\', '/').rsplit('/', 1)[-1]
        when = datetime.fromisoformat(saved_utc).astimezone(cls.zone).strftime('%H:%M:%S IST')
        return f'{name} at {when}'

    def record(self, message):
        self.events.append(f'{self.stamp()} IST  {message}')

    def update(self, event, key, states, active):
        if self.publisher is None:
            return False
        try:
            self.states, self.active = states, tuple(active)
            if event == 'resumed':
                self.record('RESUMED · saved answers reused; request history preserved')
            elif event == 'started':
                self.starts[key] = time.monotonic()
            elif event == 'saved':
                state = states[key]
                case, model = json.loads(key)
                duration = max(0, time.monotonic() - self.starts.pop(key, time.monotonic()))
                status, value = state['status'], state.get('value', {})
                from radle_error_evidence import evidence_summary
                reason = evidence_summary(key, state)
                reason = reason.replace('_', ' ')
                if status in {'success', 'flagged'}:
                    self.last_save = time.monotonic()
                    detail = f'SAVED · Case {case} · {model.replace("_", " ")} · {duration:.0f}s'
                    if status == 'flagged':
                        detail += f' · flag: {reason}'
                else:
                    action = {'retry': f'retry queued; {state["attempts"]}/{self.max_attempts} attempts used',
                              'uncertain': 'held for review; other jobs continue',
                              'quota': 'credit issue; dispatch paused',
                              'blocked': 'access/request issue; dispatch paused',
                              'terminal': 'attempt limit reached; review needed',
                              'rejected': 'case held for review; other jobs continue',
                              'failed': 'repair finished unsuccessfully; other jobs continue'}[status]
                    detail = f'{status.upper()} · Case {case} · {model.replace("_", " ")} · {reason} → {action}'
                self.record(detail)
            # Historical holds are not evidence that the scheduler is paused.
            self.phase = 'PAUSING · saving active requests' if event == 'pausing' else 'RUNNING'
            if event == 'stopped':
                self.phase = ('COLLECTED · final backup pending' if all(v['status'] in {'success', 'flagged'} for v in states.values())
                              else 'COMPLETE WITH FAILURES' if all(v['status'] in {'success', 'flagged', 'failed'} for v in states.values())
                              else 'REPAIR PENDING' if self.repair_enabled and not any(v['status'] in {'quota', 'blocked'} for v in states.values())
                              else 'STOPPED · saved progress retained; see outstanding work below')
            self.draw()
            return True
        except Exception:
            self.publisher = None
            print('Live display unavailable; continuing with console progress.', flush=True)
            return False

    def saved_backup(self, path, saved_utc):
        if self.publisher is None:
            return False
        try:
            self.backup = self.backup_label(path, saved_utc)
            self.record('BACKUP · ' + self.backup)
            if self.phase == 'COLLECTED · final backup pending':
                self.phase = 'COMPLETE'
            self.draw()
            return True
        except Exception:
            self.publisher = None
            return False

    def render(self):
        states, active = self.states, set(self.active)
        counts = Counter(v['status'] for k, v in states.items() if k not in active)
        total = len(self.models) * len(self.cases)
        saved = total - len(states) + counts['success'] + counts['flagged']
        done = sum(all(states[k]['status'] in {'success', 'flagged'} for k in keys)
                   for keys in self.jobs_by_case.values())
        fill = int(20 * saved / total) if total else 20
        percent = 100 * saved / total if total else 100
        lines = [f'BENCHMARK · {len(self.cases)} cases × {len(self.models)} models · {self.phase}', '',
                 f'Answers saved  {saved:,} / {total:,}  {"█" * fill}{"░" * (20 - fill)}  {percent:.0f}%',
                 f'Cases complete {done} / {len(self.cases)} · Requests active {len(active)} / {self.slots}', '']
        rows = []
        for model in self.models:
            name = model['name']
            keys = self.by_model[name]
            complete = len(self.cases) - len(keys) + sum(states[k]['status'] in {'success', 'flagged'} for k in keys)
            running = [k for k in self.active if k in keys]
            activity = '; '.join(f'Case {json.loads(k)[0]} · {max(0, time.monotonic() - self.starts.get(k, time.monotonic())):.0f}s'
                                 f' · try {states[k]["attempts"]}/{states[k].get("repair_attempt", self.max_attempts)}' for k in running)
            waiting = any(states[k]['status'] in {'pending', 'retry'} and queue.has_attempt(states[k], self.max_attempts) for k in keys)
            if not activity:
                activity = 'Complete' if complete == len(self.cases) else (
                    'Waiting for slot' if waiting and self.phase == 'RUNNING' else 'Awaiting review' if not waiting else 'Idle')
            if not running and not waiting and complete != len(self.cases):
                activity = 'Finished with failures' if all(states[k]['status'] in {'success', 'flagged', 'failed'} for k in keys) else ('Held or exhausted; run stopped' if self.phase == 'STOPPED' else 'Awaiting eligibility review' if self.repair_enabled else activity)
            if name not in self.active_models:
                activity = 'Paused this run'
            mc = Counter(states[k]['status'] for k in keys if k not in active)
            attention = [f'{mc[k]} {label}' for k, label in [('retry', 'retry'), ('uncertain', 'held'),
                         ('quota', 'credit'), ('blocked', 'blocked'), ('terminal', 'exhausted'), ('rejected', 'rejected'), ('failed', 'failed'), ('flagged', 'flagged')] if mc[k]]
            rows.append([str(model.get('display_name') or name.replace('_', ' ')), f'{complete} / {len(self.cases)}',
                         activity, ', '.join(attention) or '—'])
        table = [['MODEL', 'SAVED', 'ACTIVITY', 'ATTENTION']] + rows
        widths = [max(len(row[i]) for row in table) for i in range(3)]
        lines.extend('  '.join(row[i].ljust(widths[i]) for i in range(3)) + '  ' + row[3] for row in table)
        held = sum(counts[k] for k in ('uncertain', 'quota', 'blocked', 'terminal', 'rejected'))
        last = f'{max(0, time.monotonic() - self.last_save):.0f}s ago' if self.last_save is not None else 'No new answer this session'
        hold_label = 'awaiting repair' if self.repair_enabled else 'need review'
        runnable, exhausted = waiting_counts(states, active, self.max_attempts)
        cooling = sum(policy['until'] > time.time() for policy in queue.model_pacing(states).values())
        lines += ['', f'Waiting: {runnable} queued · {exhausted} exhausted · {cooling} models cooling down · {held} {hold_label} · {counts["failed"]} failed',
                  f'Last answer saved: {last}', f'Last backup: {self.backup}',
                  f'Updated: {self.stamp()} IST · refresh every 5s while collecting', '', 'RECENT EVENTS', *self.events]
        return '\n'.join(lines)

    def draw(self):
        content = {'text/plain': self.render()}
        if self.handle is None:
            self.handle = self.publisher(content, raw=True, display_id=True)
            if self.handle is None:
                raise RuntimeError('Notebook display did not return an update handle')
        else:
            self.handle.update(content, raw=True)


def collect(rb, *, client, image_folder, output_csv, models, test_limit=None,
            prompt=None, max_output_tokens=16384, universal_temperature=.01,
            backup_dir=None, concurrency=2, max_attempts=3, migration=None,
            stop=None, resume_blocked=False, repair_once=False, repair_round=1, allow_partial_result=False, retry_authorization=None):
    """One request per attempt. CSV is derived from baseline + journal.

    Attempts are counted durably from journal creation. Pre-journal failures are
    retained in the baseline; their historical attempt count is not guessed.
    Unknown request outcomes stop before inference. Native SDKs remain on the legacy lane
    until their concurrency contracts have separately been tested.
    """
    if (retry_authorization is not None or (repair_once and repair_round == 4)) and not resume_blocked:
        raise RuntimeError('Paid repair requires the existing billing preflight before dispatch.')
    output_csv = Path(output_csv)
    folder = Path(str(output_csv) + '.concurrent')
    folder.mkdir(parents=True, exist_ok=True)
    if not models or len({m['name'] for m in models}) != len(models):
        raise ValueError('Empty or duplicate model names')
    if any(rb.uses_native_openai(m) or rb.uses_native_anthropic(m) or rb.uses_native_google(m) for m in models):
        raise ValueError('Concurrent mode currently requires OpenAI-compatible provider clients')
    history_path = output_csv.parent / 'replacement_history.json'
    previous_attempts = json.loads(history_path.read_text(encoding='utf-8')).get('previous_attempts', {}) if history_path.exists() else {}
    stop = stop or threading.Event()
    prompt = rb.PROMPT if prompt is None else prompt
    image_index = rb.build_image_index(image_folder)
    cases = sorted(image_index, key=rb.numeric_case_sort_key)
    if test_limit:
        cases = cases[:test_limit]
    if not cases:
        raise ValueError('No benchmark images')
    base_rows = {case: rb.rebuild_base_row(case, image_index[case]) for case in cases}
    full_image_hashes = {case: [digest(p) for p in image_index[case]] for case in cases}
    # SDK retries would otherwise multiply the persisted scheduler budget.
    single_client = client.with_options(max_retries=0, timeout=600)
    active_model_names = {m['name'] for m in models}
    with queue.writer_lock(folder):
        journal = folder / 'queue' / 'events.jsonl'
        if journal.exists():
            with journal.open(encoding='utf-8') as saved:
                original_models = json.loads(saved.readline())['contract']['models']
            original_by_name = {m['name']: m for m in original_models}
            if active_model_names < set(original_by_name):
                if any(queue.encode(m) != queue.encode(original_by_name[m['name']]) for m in models):
                    raise ValueError('Run identity changed; selected model settings differ from original journal')
                # Selection changes dispatch only; replay/export still use the full frozen roster.
                models = original_models
        baseline = folder / 'baseline.csv'
        receipt_path = folder / 'baseline.json'
        if not receipt_path.exists():
            if (folder / 'queue' / 'events.jsonl').exists():
                raise RuntimeError('Missing baseline receipt for existing journal')
            if baseline.exists():
                raise RuntimeError('Incomplete baseline initialization; inspect before recovery')
            if output_csv.exists():
                if migration and digest(output_csv) != migration['baseline_sha256']:
                    raise RuntimeError('Migration source hash differs from witnessed checkpoint')
                shutil.copyfile(output_csv, baseline)
            else:
                rb.atomic_to_csv(pd.DataFrame(list(base_rows.values())), str(baseline))
            with baseline.open('r+b') as handle:
                os.fsync(handle.fileno())
            atomic_json(receipt_path, {'sha256': digest(baseline), 'migration': migration or {},
                                      'created_utc': datetime.now(timezone.utc).isoformat()})
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if digest(baseline) != receipt['sha256']:
            raise RuntimeError('Frozen baseline changed')
        if migration is not None and migration != receipt['migration']:
            raise RuntimeError('Migration receipt changed')
        migration = receipt['migration']
        df = pd.read_csv(baseline, dtype=str, keep_default_na=False).astype('object')
        if 'Master_Case_ID' not in df or df['Master_Case_ID'].duplicated().any():
            raise ValueError('Invalid or duplicate baseline case IDs')
        jobs, initial_attempts, legacy_failures = [], {}, []
        model_by_name = {m['name']: m for m in models}
        for case in cases:
            df, row_index = rb._get_or_create_case_row(df, case)
            for column, value in base_rows[case].items():
                old = rb.safe_str(df.at[row_index, column]) if column in df else ''
                if old and old != value:
                    raise ValueError(f'Case/image identity changed: {case}/{column}')
                df.at[row_index, column] = value
            for model in models:
                name = model['name']
                row = df.loc[row_index]
                info = rb.classify_cell_for_audit(row, name, attempts=0,
                    max_output_tokens=max_output_tokens,
                    require_token_usage=rb.requires_positive_token_usage(model),
                    require_readable_reasoning=model.get('require_readable_reasoning', False))
                if info['bucket'] == 'no_paid_cleanup':
                    if not rb.apply_no_paid_cleanup_to_cell(df, row_index, name, info):
                        raise RuntimeError(f'Unresolved offline cleanup: {case}/{name}')
                    continue
                if not info.get('needs_api_repair'):
                    continue
                job = queue.Job(case, name, {'model': model, 'images': full_image_hashes[case],
                                            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()})
                diagnosis = rb.safe_str(row.get(f'Diagnosis_{name}', '')).strip()
                previous = migration.get('initial_attempts', {}).get(job.key)
                if diagnosis and previous is None:
                    legacy_failures.append(job.key)
                if job.key in migration.get('uncertain_jobs', []):
                    raise RuntimeError(f'Uncertain pre-migration request: {case}/{name}')
                if previous is not None:
                    initial_attempts[job.key] = previous
                jobs.append(job)
        row_by_case = {str(row['Master_Case_ID']): i for i, row in df.iterrows()}
        contract = {'baseline_sha256': receipt['sha256'], 'cases': cases, 'models': models,
                    'images': full_image_hashes, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                    'max_output_tokens': max_output_tokens, 'temperature': universal_temperature,
                    'source_sha256': digest(rb.__file__), 'adapter_sha256': digest(__file__),
                    'scheduler_sha256': digest(queue.__file__)}
        applied = {}
        exported_cases = set()
        jobs_by_case = {case: [j.key for j in jobs if j.case == case] for case in cases}
        latest_states = {}
        starts = {}
        live = LiveProgress(models, cases, jobs, jobs_by_case, concurrency, max_attempts, folder / 'checkpoint.json')
        live.active_models = active_model_names
        live.repair_enabled = repair_once
        def log(message):
            print(f'[{LiveProgress.stamp()} IST] ' + message, flush=True)

        def progress(event, key, states, active):
            if event == 'started':
                starts[key] = time.monotonic()
            elapsed = max(0, time.monotonic() - starts.pop(key, time.monotonic())) if event == 'saved' else 0
            if live.update(event, key, states, active):
                return
            if event == 'heartbeat' and time.monotonic() - progress.last_console < 30:
                return
            if event == 'heartbeat':
                progress.last_console = time.monotonic()
            if event == 'started':
                case, name = json.loads(key)
                log(f"RUNNING  case {case} | {name.replace('_', ' ')} | attempt {states[key]['attempts']}/{max_attempts}")
            elif event == 'saved':
                state = states[key]
                case, name = json.loads(key)
                value = state['value']
                labels = {'success': 'OK', 'flagged': 'OK + FLAG', 'retry': 'RETRY WAIT',
                          'uncertain': 'REVIEW', 'quota': 'PAUSE', 'blocked': 'PAUSE', 'terminal': 'EXHAUSTED', 'rejected': 'CASE REJECTED', 'failed': 'FAILED'}
                from radle_error_evidence import evidence_summary
                detail = evidence_summary(key, state)
                if detail:
                    detail = detail.replace('_', ' ')
                if state['status'] == 'retry':
                    detail += f"; eligible in {max(0, round(state['ready_at'] - time.time()))}s, when a slot is free"
                log(f"{labels[state['status']]}  case {case} | {name.replace('_', ' ')} | {elapsed:.1f}s | {detail} | saved")
                evidence = value.get('diagnostic') or {}
                if 'output_tokens' in evidence:
                    log(f"  Output tokens: {evidence['output_tokens']} / {evidence.get('max_output_tokens', '?')}")
                if evidence.get('archive'):
                    log(f"  Evidence: {evidence['archive']}")
                if state['status'] in {'quota', 'blocked'}:
                    log('PAUSING: account/access problem; waiting for in-flight responses to be saved.')
                elif state['status'] == 'uncertain':
                    log('HELD for targeted review; other jobs continue. This request will not be blindly resent.')
            if event in {'resumed', 'saved', 'heartbeat', 'stopped'}:
                log(progress_summary(states, active, jobs_by_case, len(cases) * len(models), len(cases), repair_enabled=repair_once, max_attempts=max_attempts))
            if event == 'heartbeat' and active:
                log('Still waiting: ' + '; '.join(
                    f"case {json.loads(k)[0]} / {json.loads(k)[1].replace('_', ' ')} ({time.monotonic() - starts.get(k, time.monotonic()):.0f}s)"
                    for k in active))

        progress.last_console = time.monotonic()

        def export():
            # Keep original baseline column order, then deterministic added columns.
            old_columns = list(pd.read_csv(baseline, nrows=0).columns)
            columns = old_columns + sorted(c for c in df if c not in old_columns)
            final = rb._sort_benchmark_df(df.reindex(columns=columns))
            path = rb.save_benchmark_progress(final, str(output_csv), numbered=True, backup_dir=backup_dir)
            atomic_json(folder / 'checkpoint.json', {'csv_sha256': digest(output_csv),
                'numbered_backup': str(path), 'saved_utc': datetime.now(timezone.utc).isoformat(),
                'states': {k: {'status': v['status'], 'attempts': v['attempts']} for k, v in latest_states.items()}})
            if not live.saved_backup(path, datetime.now(timezone.utc).isoformat()):
                log(f'BACKUP SAVED: {path}')
            return final

        def checkpoint(states):
            nonlocal latest_states, df
            latest_states = states
            for key, state in states.items():
                fields = state['value'].get('fields', {})
                if not fields:
                    continue
                # Starting another attempt retains the prior result until its replacement arrives.
                # Cache the fields themselves, not the active attempt counter.
                field_hash = hashlib.sha256(queue.encode(fields).encode('utf-8')).hexdigest()
                if applied.get(key) == field_hash:
                    continue
                case, name = json.loads(key)
                df = rb._assign_row_values(df, row_by_case[case], fields)
                applied[key] = field_hash
            finished_cases = {case for case, keys in jobs_by_case.items() if keys and
                all(states[k]['status'] in {'success', 'flagged', 'terminal', 'rejected', 'failed'} for k in keys)}
            if len(finished_cases - exported_cases) >= rb.CHECKPOINT_CASE_INTERVAL:
                export()
                exported_cases.update(finished_cases)

        def call(job, attempt):
            model = model_by_name[job.model]
            from radle_attempt_artifacts import new_identity, persist
            artifacts = folder / 'attempt_artifacts'
            try:
                content = rb.build_content_array(job.case, image_index, prompt=prompt)
                params = rb.build_api_params(model, content, max_output_tokens, universal_temperature)
                identity = new_identity(job.case, job.model, attempt, params)
                prepared = persist(artifacts, identity, 'prepared', {'api_surface': model.get('api_surface', 'chat_completions')})
                dispatch = persist(artifacts, identity, 'dispatch_entered', {'prepared': prepared})
            except Exception as exc:
                return queue.Outcome('blocked', {'error_type': type(exc).__name__,
                    'execution_stage': 'local_preparation', 'request_sent': False,
                    'remote_outcome_unknown': False})
            previous = previous_attempts.get(json.dumps([job.case, job.model], separators=(',', ':')), 0)
            new_attempt = attempt - initial_attempts.get(job.key, 0)
            attempt_history = {'prior_attempts': previous, 'new_attempt': new_attempt, 'collection_attempt': attempt, 'cumulative_attempt': previous + new_attempt, 'is_replacement_retry': previous > 0, 'max_output_tokens': max_output_tokens}
            t0 = time.time()
            try:
                if model.get('api_surface') == 'responses':
                    response = rb.call_openrouter_responses(single_client, params,
                        dict(model, response_archive_dir=str(artifacts / 'responses')))
                else:
                    response = single_client.chat.completions.create(**params)
            except Exception as exc:
                funds = None
                if getattr(exc, 'radle_response_receipt', None):
                    from radle_attempt_artifacts import read_verified
                    original = read_verified(exc.radle_response_receipt)
                    received = persist(artifacts, identity, 'response_received', original['payload'])
                    return queue.Outcome('blocked', {'error_type': type(exc).__name__,
                        'execution_stage': 'local_response_processing', 'response_received': True,
                        'remote_outcome_unknown': False, 'response_receipt': received,
                        'request_identity': identity, 'dispatch_receipt': dispatch,
                        'attempt_history': attempt_history})
                status = getattr(exc, 'status_code', None)
                message = str(exc).lower()
                body = getattr(exc, 'body', None)
                typed_error = body.get('error', body) if isinstance(body, dict) else {}
                typed_metadata = typed_error.get('metadata') or {} if isinstance(typed_error, dict) else {}
                limit_source = typed_metadata.get('limit_source') if isinstance(typed_metadata, dict) else None
                case_failure = rb.case_rejection_diagnostic(getattr(exc, 'body', None))
                if case_failure and status not in {401, 402}:
                    exc.radle_diagnostic = case_failure
                if (getattr(exc, 'radle_diagnostic', {}) or {}).get('category') == 'case_rejected':
                    kind = 'rejected'
                elif (getattr(exc, 'radle_diagnostic', {}) or {}).get('category') == 'output_limit':
                    kind = 'retry'
                elif status == 402 and limit_source == 'openrouter_in_flight_budget':
                    kind = 'retry'
                elif status == 402 and limit_source in {'openrouter_key_limit', 'openrouter_credits'}:
                    funds = check_openrouter_funds(single_client)
                    kind = 'quota'
                elif status == 402 or (status == 403 and any(x in message for x in ('limit exceeded', 'quota', 'balance', 'budget'))):
                    funds = check_openrouter_funds(single_client)
                    kind = 'retry' if funds['status'] == 'available' else 'quota'
                elif status == 403:
                    # An unexplained request refusal is not proof the whole account is broken.
                    # Hold this pair without resending; unrelated work can continue.
                    account_issue = any(x in message for x in (
                        'authentication', 'api key', 'api_key', 'allowlist', 'ip address', 'access'))
                    kind = 'blocked' if account_issue else 'uncertain'
                elif status in {400, 401, 404, 422}:
                    kind = 'blocked'
                elif status in {429, 500, 502, 503, 504}:
                    kind = 'retry'
                else:
                    # A dropped connection/stream may already have incurred inference.
                    kind = 'uncertain'
                delay = min(60, 2 ** min(attempt, 6))
                if funds is not None and kind == 'retry':
                    delay = 30
                if status in {429, 503} or (status == 402 and limit_source == 'openrouter_in_flight_budget'):
                    headers = getattr(getattr(exc, 'response', None), 'headers', {}) or {}
                    delay = retry_delay(headers.get('retry-after'), attempt)
                headers = getattr(getattr(exc, 'response', None), 'headers', {}) or {}
                body = getattr(exc, 'body', None)
                error = body.get('error', body) if isinstance(body, dict) else {}
                typed_metadata = error.get('metadata') or {} if isinstance(error, dict) else {}
                from radle_error_evidence import code
                error_evidence = {'http_status': status, 'error_type': type(exc).__name__,
                    'provider_error_code': code(error.get('code')) if isinstance(error, dict) else None,
                    'limit_source': code(typed_metadata.get('limit_source')) if isinstance(typed_metadata, dict) else None,
                    'retry_after': str(headers.get('retry-after'))[:128] if headers.get('retry-after') is not None else None}
                try:
                    error_receipt = persist(artifacts, identity, 'request_error', error_evidence)
                except Exception:
                    error_receipt = None
                return queue.Outcome(kind, {'http_status': status, 'error_type': type(exc).__name__, 'diagnostic': diagnostic(exc), 'attempt_history': attempt_history, 'credit_check': funds,
                    'execution_stage': 'request_error', 'request_identity': identity, 'dispatch_receipt': dispatch,
                    'error_receipt': error_receipt, 'limit_source': error_evidence['limit_source'],
                    'retry_after_header': error_evidence['retry_after'],
                    'provider_error_code': error_evidence['provider_error_code']},
                                     retry_after=delay if kind == 'retry' else 0)
            response_receipt = None
            try:
                response_receipt = persist(artifacts, identity, 'response_received',
                    getattr(response, '_radle_original_response', response),
                    sensitive_values=(getattr(single_client, 'api_key', None),))
                from radle_attempt_artifacts import jsonable, response_metadata as observe_response
                response_metadata = observe_response(jsonable(getattr(response, '_radle_original_response', response)))
                fields = rb.extract_result(response, round(time.time() - t0, 1), params, False, model)
                info = rb.classify_cell_for_audit(pd.Series(fields), job.model, attempts=0,
                    max_output_tokens=max_output_tokens,
                    require_token_usage=rb.requires_positive_token_usage(model),
                    require_readable_reasoning=model.get('require_readable_reasoning', False))
            except Exception as exc:
                return queue.Outcome('blocked', {'error_type': type(exc).__name__,
                    'execution_stage': 'local_response_processing', 'response_received': True,
                    'remote_outcome_unknown': False, 'response_receipt': response_receipt,
                    'request_identity': identity, 'dispatch_receipt': dispatch,
                    'attempt_history': attempt_history})
            if info['bucket'] == 'accepted':
                kind = 'success'
            elif not info.get('needs_api_repair'):
                kind = 'flagged'
            elif info['bucket'] == 'no_paid_cleanup':
                kind = 'blocked'
            else:
                kind = 'retry'
            from radle_error_evidence import number
            if (kind == 'retry' and response_metadata.get('content_length') == 0
                    and response_metadata.get('finish_reason') == 'length'
                    and (number(response_metadata.get('completion_tokens')) or 0) >= max_output_tokens):
                # An identical immediate retry cannot repair a known budget stop.
                kind = 'terminal'
                info = dict(info, reason='output_cap_reached_without_final_answer')
            try:
                persist(artifacts, identity, 'validated', {'classification': kind,
                    'reason': info['reason'], 'response_receipt': response_receipt})
            except Exception as exc:
                return queue.Outcome('blocked', {'error_type': type(exc).__name__,
                    'execution_stage': 'local_validation_commit', 'response_received': True,
                    'remote_outcome_unknown': False, 'response_receipt': response_receipt,
                    'request_identity': identity, 'dispatch_receipt': dispatch,
                    'attempt_history': attempt_history})
            return queue.Outcome(kind, {'fields': rb.make_json_safe(fields), 'reason': info['reason'], 'response_metadata': response_metadata, 'attempt_history': attempt_history,
                'execution_stage': 'validated', 'response_received': True,
                'request_identity': identity, 'dispatch_receipt': dispatch, 'response_receipt': response_receipt},
                                 retry_after=2 if kind == 'retry' else 0)

        print(f'Concurrent collection: {len(jobs)} journal jobs, {concurrency} slots; ordinary limit {max_attempts} attempts/job. Additional explicit repair grants are retained separately in the journal.', flush=True)
        if legacy_failures:
            print(f'Preserved {len(legacy_failures)} pre-journal failures; historical attempts remain in the original logs.', flush=True)
        paused_models = sorted(set(model_by_name) - active_model_names)
        if paused_models:
            log('Paused models this run (saved history retained): ' + ', '.join(paused_models))
        if resume_blocked:
            funds = check_openrouter_funds(single_client)
            atomic_json(folder / 'resume_credit_check.json', funds)
            if funds['status'] != 'available':
                raise RuntimeError('Resume paused: billing check is exhausted or unavailable; see resume_credit_check.json.')
            log('RESUME: billing check passed; original attempt limits retained.')
        queue_options = dict(concurrency=concurrency, max_attempts=max_attempts,
                             initial_attempts=initial_attempts, contract=contract, stop=stop,
                             resume_blocked=resume_blocked, checkpoint=checkpoint,
                             on_event=progress, heartbeat_seconds=5,
                             selected_keys={j.key for j in jobs if j.model in active_model_names})
        if resume_blocked:
            from radle_journal_recovery import recover
            queue_options['journal_recovery'] = lambda journal, manifest: recover(
                queue, journal, manifest, output_csv, folder / 'checkpoint.json')
        if retry_authorization is not None:
            if repair_once:
                raise ValueError('Choose explicit retry policy or legacy repair, not both')
            from radle_retry_policy import validate
            validate(retry_authorization)
            log(f"RETRY PASS {retry_authorization['id']}: up to {retry_authorization['attempts_per_pair']} spaced attempts per eligible pair; saved answers/refusals protected.")
            result = queue.run(jobs, call, folder / 'queue', retry_authorization=retry_authorization, **queue_options)
        else:
            result = queue.run(jobs, call, folder / 'queue', **queue_options)
        if repair_once and not result['paused']:
            log(f'REPAIR ROUND {repair_round}: one authorized attempt per eligible pair; unselected held or exhausted states remain unchanged.')
            previous_calls = result['calls']
            repair_options = dict(queue_options)
            repair_options['selected_keys'] = {
                key for key, state in result['states'].items()
                if key in queue_options['selected_keys']
                and (state['status'] == 'terminal' or 'repair_attempt' in state)}
            result = queue.run(jobs, call, folder / 'queue', repair_once=True, repair_round=repair_round, **repair_options)
            result['calls'] += previous_calls
        checkpoint(result['states'])
        final_df = export()
        counts = dict(Counter(v['status'] for v in result['states'].values()))
        atomic_json(folder / 'status.json', {'complete': result['complete'], 'paused': result['paused'],
                    'new_calls': result['calls'], 'counts': counts, 'concurrency': concurrency,
                    'legacy_failures': legacy_failures, 'attempt_budget_scope': 'journal',
                    'updated_utc': datetime.now(timezone.utc).isoformat()})
        from radle_error_evidence import evidence_summary
        failed_pairs = []
        for key, state in result['states'].items():
            if state['status'] == 'failed':
                case, name = json.loads(key)
                value = state['value']
                failed_pairs.append({'Master_Case_ID': case, 'model': name, 'status': 'failed',
                    'attempts': state['attempts'], 'http_status': value.get('http_status'),
                    'reason': evidence_summary(key, state)})
        atomic_json(folder / 'failed_pairs.json', failed_pairs)
        from radle_error_evidence import evidence_record
        failure_evidence = [evidence_record(key, state, max_output_tokens)
                            for key, state in result['states'].items()
                            if state['status'] not in {'success', 'flagged'}]
        atomic_json(folder / 'failure_evidence.json', failure_evidence)
        final_df.attrs['failure_evidence'] = failure_evidence
        final_df.attrs['failure_evidence_path'] = str(folder / 'failure_evidence.json')
        final_df.attrs['failed_pairs'] = failed_pairs
        final_df.attrs['failed_pairs_path'] = str(folder / 'failed_pairs.json')
        unresolved = []
        for key, state in result['states'].items():
            if state['status'] not in {'success', 'flagged'}:
                case, name = json.loads(key)
                unresolved.append({'Master_Case_ID': case, 'model': name,
                    'status': state['status'], 'attempts': state['attempts'],
                    'category': 'exhausted' if state['status'] in {'pending', 'retry'} and not queue.has_attempt(state, max_attempts) else state['status']})
        final_df.attrs['unresolved_pairs'] = unresolved
        final_df.attrs['unresolved_pairs_path'] = str(folder / 'unresolved_pairs.json')
        atomic_json(folder / 'unresolved_pairs.json', unresolved)
        if result['paused'] or not result['complete'] or any(v['status'] == 'terminal' for v in result['states'].values()):
            log('REVIEW REQUIRED. Completed answers are saved; unresolved requests were not blindly resent.')
            for key, state in result['states'].items():
                if state['status'] in {'uncertain', 'quota', 'blocked', 'terminal', 'rejected'}:
                    case, name = json.loads(key)
                    from radle_error_evidence import evidence_summary
                    detail = evidence_summary(key, state)
                    log(f"  case {case} | {name.replace('_', ' ')}: {detail}")
            log(f"Evidence journal: {folder / 'queue' / 'events.jsonl'}")
            log('Next: review the listed request evidence before resuming. Do not delete the journal or rerun uncertain calls blindly.')
            if not allow_partial_result:
                raise RuntimeError('Collection has unresolved outcomes; completed answers saved. See the case-specific explanation above.')
        if failed_pairs:
            log(f'COLLECTION COMPLETE WITH FAILURES: {len(failed_pairs)} pairs failed after the bounded repair pass. Saved answers retained.')
        return final_df
