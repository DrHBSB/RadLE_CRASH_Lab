# Gemini-only transport and zero OpenRouter spending

## Current State
2026-10-16 root: Direct Gemini generateContent adapter implemented behind the existing durable scheduler. Canonical notebook never loads OPENROUTER_API_KEY and cannot fall back to OpenRouter. Existing historical contracts remain frozen; actual direct provider/model/request/transport recorded on new responses. Completed run remains read-only. Focused tests pass; publish immutable release and hand off link, live acceptance pending.

## Locked Facts
User forbids any OpenRouter spending and authorizes Gemini key for Argon repairs. Preserve 200 saved answers, frozen model contract, existing policy ID, unused attempts only, cap32768 and reasoning ladder. No fallback to OpenRouter, no new repair allowance. Full-response/private receipts must expose actual direct provider/model and route. Completed saved run remains read-only. No promotion/export/judge.

## Do Not Revisit
Do not rename grant IDs, reset history, replace saved flagged answers, or retry held unknown outcomes. Do not rewrite old provider fields.

## Progress
2026-10-16 root: Google read-only models endpoint confirms models/gemini-4-argon, generateContent, thinking enabled, outputTokenLimit32768. Existing OpenRouter global endpoint unavailable. Google generateContent documentation and existing native Google implementation inform request mapping.

## Surprises & Discoveries
2026-10-16 root: Existing concurrent collector assumes OpenRouter billing/client. Use a bounded explicit transport interface, preserving journal model identity while logging actual native request and provider on each new response.

## Decision Log
2026-10-16 root: Native generateContent is used to capture final text and thought summaries separately with original response retained. Google metadata authentication is not a balance check; errors remain held under existing scheduler policy.

## Revision Notes
2026-10-16 root: Initial plan. Worktree codex/radle-journal-recovery. Only transport, admission hooks, canonical notebook, dedicated tests and this plan are in scope.

## Outcomes & Retrospective
Seven mocked transport tests pass, including a real scheduler fixture consuming exactly two ordinary plus two existing bounded repair attempts, repeated rerun adding zero calls, refusal/unknown response capture, provenance and zero OpenRouter calls. Eight admission, two flagged-completion and eleven surgical tests pass (28 total). Notebook cells compile in admission/transport tests; diff check passes. No paid inference executed. Release tag codex/radle-gemini-only-20261016; live Colab acceptance remains pending.

## Suggested Skills By Phase
workflow-router and execplan used for implementation scope; existing notebook discipline retained.
