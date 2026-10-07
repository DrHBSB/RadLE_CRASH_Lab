# Prepare the 15-model Colab release

This plan follows ~/.codex/PLANS.md. The user authorized Colab and Git preparation on 2026-10-07; collection is launched by the user.

## Current State

2026-10-07, Codex: Notebook and scoped runtime mapping prepared in existing C:/tmp/radle_muse13_colab. Next: offline contract tests, authenticated metadata refresh, commit and publish branch plus immutable release tag.

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
