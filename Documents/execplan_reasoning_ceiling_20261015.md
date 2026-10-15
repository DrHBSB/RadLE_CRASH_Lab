# Reasoning step-down after repeated confirmed output ceilings

## Purpose

Use existing authorized retries more effectively after repeated token ceilings, without raising the output cap, changing clinical inputs, or creating more attempts. Each case-model pair remains independent. The user approved the playback: after two confirmed ceiling hits including collection history, lower effort by one supported level for the next authorized retry; after another ceiling hit lower once again. Other errors retain the selected effort. Never disable readable reasoning.

## Current State

2026-10-15 root: implementing on existing worktree C:/Users/thehb/.codex/worktrees/radle-journal-recovery/RadLE v2, branch codex/radle-journal-recovery, parent94eb394. Active old Colab releasec87d9fd had3130/3200saved143completecases at13:11IST. Sent one graceful Interrupt execution while Qwenmax31 was active; wait for drain/finalbackup. User subsequently closed old tab and authorized a new tab when ready. Do not infer runtime shutdown from tab closure. Current authorization radle-user-broad-retry-20261015 remains identical:max77pairs,two new attempts,60second same-pair spacing,concurrency1. No new grant. Need publish aligned immutable notebook/Python, reconnect and verify oldexecutionended before newcollector. Current output limit32768 remains.

## Locked Facts

User's explicit approval supersedes earlier reasoning-freeze only for confirmed-ceiling-triggered reductions. Existing immutable contract remains the original cohort/request baseline; runtime request copies may change only authorized reasoning effort and must record that deviation. Saved/flagged answers, refusals, unknown/credit holds and all history remain protected. HTTP errors, parse labels, empty answers and missing token metadata do not by themselves prove ceiling hits. Evidence must report completion tokens reaching the recorded request output cap, without a contradictory non-length finish reason. Never count duplicated archive/snapshot records or copied old CSV evidence as separate responses.

## Do Not Revisit

No increased token cap, hidden reasoning disable, extra paid authorization, model/provider/input/privacy changes, direct browser code edit, manual Drive edit, history deletion or unknown lock retirement. No promotion/export/judging. Keep policy source general, never special-case caseIDs,Claude or today's repair round.

## Implementation and verification

Use a small reusable reasoning-ceiling helper. Read supported_efforts from current public OpenRouter model catalog (existing preflight already checks it); order supported enabled levels using minimal,low,medium,high,xhigh,max,excluding none. No supported controllable effort means unchanged/logged; do not invent an effort level. Use a private runtime model copy. Read verified archive ledger once and maintain per-pair observations for the current execution. Confirmed distinct historical hits initialize eligibility; the first newly adaptive request lowers exactly one step even if many old max hits exist. Persist selected effort, previous effort, hit count, last handled hit count, policyversion and evidence source in prepared request receipt and outcome history. Subsequent HTTP/non-cap outcomes keep effort; a new cap permits one further step. At floor retain floor. Recover latest decision and count from durable artifacts/journal so restart never lowers twice for the same hit. Baseline CSV contributes at most one uniquely identified prior response, never inferred counts.

Tests: two-hit threshold,distinct pair/model isolation,one-step sparse ladder,large historical count yields one step only,non-cap errors leave effort,continued cap steps/floor,duplicate evidence ignored,CSV source copies ignored,unknown usage notzero,per-model no-control,request/cap/cohort unchanged except selected effort,private receipts and restartrestore,existing budget/replay/recovery tests. Compile canonical4cells. Publish immutable tag and commit; do not change the existing paid-pass ID. Browser only runs committed cells.

## Progress

- 2026-10-15 root: read AGENTS/globalPLANS and existing source; inspected live collector and requested graceful drain; official OpenRouter preflight exposes reasoning.supported_efforts. Implementation started.

## Surprises & Discoveries

2026-10-15 root: shared effort enum is insufficient to select a supported lower level; current model catalog is authoritative. QwenFlash uses enabled reasoning with no explicit effort control. Archived CSV fields may describe an earlier response, so attempt counts cannot substitute for confirmed hits.

## Decision Log

2026-10-15 root: preserve initial roster and contract; record authorized per-request deviation separately. No automatic budget expansion. Use one reduction per newly observed ceiling event after threshold, rather than jumping several levels based on unadapted historical count.

## Revision Notes

2026-10-15 root: initial approved implementation plan. ExecPlan and notebook skills apply; no delegation requested or needed.

## Outcomes & Retrospective

Implementation complete: nine focused reasoning tests including actual mocked collector request parameters and durable CSV metadata pass;64 retry/artifact/recovery/surgical/display regressions pass; four notebook cells compile and diff check passes. Old runtime reattached read-only in new Chrome tab171256920: Qwenmax31 saved13:14:34IST; finalbackup0041 saved13:15:54IST,3131answers,collector stopped safely. Publication and live acceptance next.

## Suggested Skills By Phase

Execplan manual for implementation/handoff. Jupyter-notebook manual for canonical notebook alignment. Computer-use manual for committed notebook execution only. Official provider docs/catalog verification required. No extra orchestration.

2026-10-15 update: user clarified only the two already authorized retries are used, not all fallback levels in one pass. Future model admission records supported levels, highest initial effort and ordered enabled fallbacks using effort_profile. Gemini Argon4 is a future admission, not added now. Existing cohort initial settings are retained.
