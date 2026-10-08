# Restore the canonical Git-backed Colab workflow

## Purpose

Restore the familiar four-cell notebook so the user can run one coherent notebook and Python release. Browser use must never edit code.

## Current State

Local restoration prepared on codex/openrouter-official-provider in C:/tmp/radle_muse13_colab. Publish tag codex/radle-16-workflow-restored-20261008, then open its canonical notebook in Colab. Inspect and drain the previous running cell before starting a second collector. Verify setup, imports, configuration and workflow in order.

## Locked Facts

Run openrouter_16_32k_20261008 has 200 cases and 16 models, cap32768, concurrency3, two attempts including carried history. Existing contract release identity is codex/radle-16-mistral-large-4-20261008; preserve it while recording the newer runtime release separately. Seed preparation returns the saved replacement_history.json when the target exists. No third attempts or promotion. Billing checks are already committed at 01e0cba.

## Do Not Revisit

Never edit notebook cells through Chrome. Local edits, Git commit/push, then refresh/open the published notebook. Preserve all Drive outputs and journals. No new cohort or migration.

## Progress

- [x] 2026-10-08 root: inspected historical209beae, initialffee0cc and current01e0cba notebook structures.
- [x] 2026-10-08 root: restored original Cell4 autonomous call and its result summaries; retained current budget, migration and privacy configuration.
- [x] 2026-10-08 root: wrote durable AGENTS.md restrictions.
- [ ] Publish release, update monitor prompt, drain old cell, open Git notebook and confirm collection progresses.

## Surprises & Discoveries

2026-10-08 root: Chrome had an old notebook with a newer exec wrapper. That lost coherent visible configuration. Old quota states can remain visible after funds recover; do not infer an account-wide failure from the dashboard label alone.

## Decision Log

2026-10-08 root: restore historical workflow presentation with current arguments; keep the existing collection contract release field unchanged so saved data resumes. Smoke remains disabled for this already-started cohort; repair and promotion remain disabled.

## Revision Notes

2026-10-08 root: created after explicit user request for Git-only edits and durable agent discipline.

## Outcomes & Retrospective

Pending runtime handoff. No local tests requested or run. Acceptance requires a fresh Git notebook with the four canonical cells, exact runtime release displayed and new saved answers in the same run journal.

## Suggested Skills By Phase

Planning: execplan. Runtime handoff: browser controls limited to open/run/monitor; no code edits. Implementation: none.
