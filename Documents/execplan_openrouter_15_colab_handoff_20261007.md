# Prepare the 15-model Colab release

This plan follows ~/.codex/PLANS.md. The user authorized Colab and Git preparation on 2026-10-07; collection is launched by the user.

## Current State

2026-10-07, Codex: User authorized replacing both GPT arms from case 1 and launching the revised Colab. Candidate uses official compatible providers with DeepSeek ZDR exceptions; readable summaries mandatory, one new attempt per pair, prior attempts preserved, compatible other answers reused. Verification and publication in progress.

## Locked Facts

- All 15 local synthetic smokes passed; response-reported cost USD 0.049557612.
- 11 arms use ZDR; Muse 1.2/1.3 and Qwen Flash/Max Prime have no listed ZDR route. User approved keeping these arms.
- Use highest supported effort; Qwen Flash enables reasoning without an unsupported effort override.
- Shared benchmark prompt/schema are unchanged; output cap remains 16384, concurrency 3.
- Dedicated Drive Runs/openrouter_15_max_20261007, pilot suffix _pilot_1. One clinical pilot case per arm is reused in the 200-case collection.
- Source checkout uses immutable release tag codex/radle-15-20261007. Exact requested IDs/provider names are enforced before saving.

## Do Not Revisit

Do not repeat the completed synthetic inferences. Do not merge or clean the dirty primary checkout. Do not launch Colab collection. Never upload credentials, images, results or reasoning to GitHub.

## Progress

- [x] (2026-10-07, Codex) Reused existing clean source checkout and prepared 15-arm settings.
- [x] (2026-10-07, Codex) Validate request construction, route rejection, notebook cells and zero-repair gate.
- [ ] (2026-10-07, Codex) Publish exact code revision and user launch instructions.

## Surprises & Discoveries

2026-10-07, Codex: Existing zero-pass repair cascade raised even on clean data; added an audited clean return. Concurrent calls bypass call_model, so route assertions belong in shared extract_result.

## Decision Log

2026-10-07, Codex: New Git branch codex/openrouter-15-model in the same worktree preserves the historical six-arm branch. User authorization to prepare Git supersedes the earlier no-publication readiness boundary. No new worktree.
2026-10-07, Codex: One transport/job attempt and zero automatic paid repair passes conserve spend and hold failures for review. Human verification remains mandatory downstream.

## Revision Notes

2026-10-07, Codex: Scoped implementation handoff supplements Documents/execplan_openrouter_15_model_readiness_20261005.md in the durable primary repository.

## Outcomes & Retrospective

Pending verification/publication. Collection outputs feed the reusable incremental admission workflow, blinded radiologist handoff, returned human decisions, private final-long master and then SVG generation. No automatic private promotion or public export. No reusable skill change needed.

## Suggested Skills By Phase

Planning: execplan (manual). Notebook preparation: jupyter-notebook (manual). Offline checks and Git publication: none.

## Validation And Acceptance

Compile every notebook code cell. Exercise all 15 request dictionaries against shared build_api_params; assert reasoning, pins, JSON, token parameter, no sampling. Test exact returned ID/provider rejection and clean zero-repair return. Run existing concurrent tests. Refresh key/catalog/endpoints/ZDR via metadata calls only. Review Git diff and exact staged paths. Push branch and tag; verify remote SHA. The user can then open the tagged Morning notebook and run cells 1–3 for Drive/key validation, then cell 4 to launch.

## Recovery

Use the same tag and RUN_LABEL to resume. Collection contract refuses changed images/prompt/models; successful pilot and full results are retained. Failed or uncertain pairs need review before any repeat. Do not change run labels merely to retry. CPU runtime is sufficient; no GPU workload is used.

## Verified readiness receipt

2026-10-07, Codex: Four offline release-contract tests and 22 existing concurrency tests passed. Live metadata recheck: valid key, 15 image-capable routes, 11 ZDR. No extra inference. Output-token ceiling if all 3000 responses hit 16384 tokens is USD 325.44; input/image costs additional. This is a cap-based bound, not an expected cost. The key reports a USD 100 configured limit; collection may stop on credit/budget exhaustion. Existing Chrome Colab tab 171255059 was disconnected and pointed to main; update it to the immutable release tag. OPENROUTER_API_KEY notebook-access switch was already enabled; its value was not inspected. User must ensure it is the fresh key.

## Official-provider correction and authorized fallback

2026-10-07: User requires compatible model-owner endpoints first, then the best compatible host with preference for ZDR when the owner cannot be used. Pins remain explicit, with automatic fallbacks disabled and data_collection deny.

- DeepSeek Vision: no owner-operated endpoint; retain tested DeepInfra/fp8 with ZDR.
- DeepSeek V4.1: owner synthetic request rejected with HTTP 404, no endpoint matching Paid model training data policy. Keep privacy policy; retain tested Fireworks with ZDR. Do not retry the rejected owner route.
- Claude Sonnet and Opus: official Anthropic synthetic checks both passed with readable reasoning.
- GPT arms: candidate pins OpenAI; official GPT-6.1 responses still omit readable summaries despite positive reasoning usage. Existing strict readable gate remains pending user policy decision.
- Candidate notebook uses an unpublished placeholder tag and separate run label. No corrected collection was launched; existing outputs remain preserved.

Evidence: private outputs/colab_health_20261007/changed_official_smokes contains exact route receipts, including DeepSeek privacy rejection. Prior Colab pilot and pre-Colab synthetic GPT-6.1 responses did contain readable summaries; their success did not establish summary reliability.

## Authorized GPT replacement implementation

Both GPT arms are cleared in a separate run openrouter_15_official_reasoning_20261007. Old CSV and journal remain untouched and copied into private superseded_evidence. replacement_history.json links prior attempts; new journal values record cumulative attempt counts and response termination metadata. Claudes from Vertex cannot be reused on Anthropic. All other cells require exact recorded request/provider/model, image/prompt identity and readable reasoning to reuse. One new request per pair, no automatic repair; missing summaries are flagged failures for admission and do not stop unrelated collection. Original GPT Sol pilot had two calls, recorded explicitly; later journal starts preserve known attempt counts. New tag codex/radle-official-reasoning-20261007.

Verification: 26 scoped release/concurrent tests passed. Snapshot seed check passed: 46 compatible answers reused, 20 previous pairs scheduled for replacement, both GPT and old Vertex Claude columns blank, GPT Sol case 1 retains two prior attempts, initialization idempotent, old journal unchanged. No additional API inferences for verification.
