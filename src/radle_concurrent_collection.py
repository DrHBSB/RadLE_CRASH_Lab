"""Durable concurrent collection for the existing Morning benchmark contracts."""
from collections import Counter, deque
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
import time

import pandas as pd

import radle_job_queue as queue


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


def progress_summary(states, active, jobs_by_case, total_jobs, total_cases):
    active = set(active)
    counts = Counter(v['status'] for k, v in states.items() if k not in active)
    collected = total_jobs - len(states) + counts['success'] + counts['flagged']
    cases_done = sum(not keys or all(states[k]['status'] in {'success', 'flagged'} for k in keys)
                     for keys in jobs_by_case.values())
    review = sum(counts[k] for k in ('uncertain', 'blocked', 'quota', 'terminal'))
    return (f"{collected}/{total_jobs} answers collected | {cases_done}/{total_cases} cases complete | "
            f"{len(active)} running | {counts['retry']} retry waiting | {review} need review | {counts['pending']} queued")



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
                reason = (value.get('diagnostic') or {}).get('summary') or value.get('reason') or 'See saved evidence'
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
                              'terminal': 'attempt limit reached; review needed'}[status]
                    detail = f'{status.upper()} · Case {case} · {model.replace("_", " ")} · {reason} → {action}'
                self.record(detail)
            self.phase = ('PAUSING · saving active requests'
                          if any(v['status'] in {'quota', 'blocked'} and json.loads(k)[1] in self.active_models
                                 for k, v in states.items()) else 'RUNNING')
            if event == 'stopped':
                self.phase = ('COLLECTED · final backup pending' if all(v['status'] in {'success', 'flagged'} for v in states.values())
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
                                 f' · try {states[k]["attempts"]}/{self.max_attempts}' for k in running)
            if not activity:
                waiting = any(states[k]['status'] in {'pending', 'retry'} for k in keys)
                activity = 'Complete' if complete == len(self.cases) else (
                    'Waiting for slot' if waiting and self.phase == 'RUNNING' else 'Awaiting review' if not waiting else 'Idle')
            if name not in self.active_models:
                activity = 'Paused this run'
            mc = Counter(states[k]['status'] for k in keys if k not in active)
            attention = [f'{mc[k]} {label}' for k, label in [('retry', 'retry'), ('uncertain', 'held'),
                         ('quota', 'credit'), ('blocked', 'blocked'), ('terminal', 'exhausted'), ('flagged', 'flagged')] if mc[k]]
            rows.append([str(model.get('display_name') or name.replace('_', ' ')), f'{complete} / {len(self.cases)}',
                         activity, ', '.join(attention) or '—'])
        table = [['MODEL', 'SAVED', 'ACTIVITY', 'ATTENTION']] + rows
        widths = [max(len(row[i]) for row in table) for i in range(3)]
        lines.extend('  '.join(row[i].ljust(widths[i]) for i in range(3)) + '  ' + row[3] for row in table)
        held = sum(counts[k] for k in ('uncertain', 'quota', 'blocked', 'terminal'))
        last = f'{max(0, time.monotonic() - self.last_save):.0f}s ago' if self.last_save is not None else 'No new answer this session'
        lines += ['', f'Waiting: {counts["pending"]} queued · {counts["retry"]} retry · {held} need review',
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
            stop=None, resume_blocked=False):
    """One request per attempt. CSV is derived from baseline + journal.

    Attempts are counted durably from journal creation. Pre-journal failures are
    retained in the baseline; their historical attempt count is not guessed.
    Unknown request outcomes stop before inference. Native SDKs remain on the legacy lane
    until their concurrency contracts have separately been tested.
    """
    output_csv = Path(output_csv)
    folder = Path(str(output_csv) + '.concurrent')
    folder.mkdir(parents=True, exist_ok=True)
    if not models or len({m['name'] for m in models}) != len(models):
        raise ValueError('Empty or duplicate model names')
    if any(rb.uses_native_openai(m) or rb.uses_native_anthropic(m) or rb.uses_native_google(m) for m in models):
        raise ValueError('Concurrent mode currently requires OpenAI-compatible provider clients')
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
                          'uncertain': 'REVIEW', 'quota': 'PAUSE', 'blocked': 'PAUSE', 'terminal': 'EXHAUSTED'}
                detail = (value.get('diagnostic') or {}).get('summary') or value.get('reason') or value.get('error_type', '')
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
                log(progress_summary(states, active, jobs_by_case, len(cases) * len(models), len(cases)))
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
                if not state['value'] or applied.get(key) == state['attempts']:
                    continue
                case, name = json.loads(key)
                fields = state['value'].get('fields', {})
                if fields:
                    df = rb._assign_row_values(df, row_by_case[case], fields)
                applied[key] = state['attempts']
            finished_cases = {case for case, keys in jobs_by_case.items() if keys and
                all(states[k]['status'] in {'success', 'flagged', 'terminal'} for k in keys)}
            if len(finished_cases - exported_cases) >= rb.CHECKPOINT_CASE_INTERVAL:
                export()
                exported_cases.update(finished_cases)

        def call(job, attempt):
            model = model_by_name[job.model]
            content = rb.build_content_array(job.case, image_index, prompt=prompt)
            params = rb.build_api_params(model, content, max_output_tokens, universal_temperature)
            t0 = time.time()
            try:
                if model.get('api_surface') == 'responses':
                    response = rb.call_openrouter_responses(single_client, params, model)
                else:
                    response = single_client.chat.completions.create(**params)
            except Exception as exc:
                status = getattr(exc, 'status_code', None)
                message = str(exc).lower()
                if (getattr(exc, 'radle_diagnostic', {}) or {}).get('category') == 'output_limit':
                    kind = 'retry'
                elif status == 402 or (status == 403 and any(x in message for x in ('limit exceeded', 'quota', 'balance'))):
                    kind = 'quota'
                elif status in {400, 401, 403, 404, 422}:
                    kind = 'blocked'
                elif status in {429, 500, 502, 503, 504}:
                    kind = 'retry'
                else:
                    # A dropped connection/stream may already have incurred inference.
                    kind = 'uncertain'
                delay = min(60, 2 ** min(attempt, 6))
                if status == 429:
                    try:
                        delay = max(delay, float(exc.response.headers.get('retry-after', delay)))
                    except (ValueError, AttributeError):
                        pass
                return queue.Outcome(kind, {'http_status': status, 'error_type': type(exc).__name__, 'diagnostic': diagnostic(exc)},
                                     retry_after=delay if kind == 'retry' else 0)
            fields = rb.extract_result(response, round(time.time() - t0, 1), params, False, model)
            info = rb.classify_cell_for_audit(pd.Series(fields), job.model, attempts=0,
                max_output_tokens=max_output_tokens,
                require_token_usage=rb.requires_positive_token_usage(model),
                require_readable_reasoning=model.get('require_readable_reasoning', False))
            if info['bucket'] == 'accepted':
                kind = 'success'
            elif not info.get('needs_api_repair'):
                kind = 'flagged'
            elif info['bucket'] == 'no_paid_cleanup':
                kind = 'blocked'
            else:
                kind = 'retry'
            return queue.Outcome(kind, {'fields': rb.make_json_safe(fields), 'reason': info['reason']},
                                 retry_after=2 if kind == 'retry' else 0)

        print(f'Concurrent collection: {len(jobs)} journal jobs, {concurrency} slots; max {max_attempts} attempts/job in this journal.', flush=True)
        if legacy_failures:
            print(f'Preserved {len(legacy_failures)} pre-journal failures; historical attempts remain in the original logs.', flush=True)
        paused_models = sorted(set(model_by_name) - active_model_names)
        if paused_models:
            log('Paused models this run (saved history retained): ' + ', '.join(paused_models))
        if resume_blocked:
            log('RESUME: recheck saved access/credit failures first within the original attempt budget.')
        result = queue.run(jobs, call, folder / 'queue', concurrency=concurrency,
                           max_attempts=max_attempts, initial_attempts=initial_attempts,
                           contract=contract, stop=stop, resume_blocked=resume_blocked,
                           checkpoint=checkpoint, on_event=progress, heartbeat_seconds=5,
                           selected_keys={j.key for j in jobs if j.model in active_model_names})
        checkpoint(result['states'])
        final_df = export()
        counts = dict(Counter(v['status'] for v in result['states'].values()))
        atomic_json(folder / 'status.json', {'complete': result['complete'], 'paused': result['paused'],
                    'new_calls': result['calls'], 'counts': counts, 'concurrency': concurrency,
                    'legacy_failures': legacy_failures, 'attempt_budget_scope': 'journal',
                    'updated_utc': datetime.now(timezone.utc).isoformat()})
        if not result['complete'] or any(v['status'] == 'terminal' for v in result['states'].values()):
            log('REVIEW REQUIRED. Completed answers are saved; unresolved requests were not blindly resent.')
            for key, state in result['states'].items():
                if state['status'] in {'uncertain', 'quota', 'blocked', 'terminal'}:
                    case, name = json.loads(key)
                    detail = (state['value'].get('diagnostic') or {}).get('summary') or state['value'].get('reason') or 'Older log has no detailed error; inspect the saved stream.'
                    log(f"  case {case} | {name.replace('_', ' ')}: {detail}")
            log(f"Evidence journal: {folder / 'queue' / 'events.jsonl'}")
            log('Next: review the listed request evidence before resuming. Do not delete the journal or rerun uncertain calls blindly.')
            raise RuntimeError('Collection has unresolved outcomes; completed answers saved. See the case-specific explanation above.')
        return final_df
