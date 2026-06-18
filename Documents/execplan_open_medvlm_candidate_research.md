# Research Open Medical Vision-Language Model Candidates

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The prompt-provided AGENTS.md instruction requires an ExecPlan for complex features, multi-step analyses, or significant refactors and prefers `Documents/`.

## Purpose / Big Picture

This research pass evaluates open or semi-open medical vision-language model candidates for a separate experimental RadLE benchmark path. The user asked specifically about LLaVA-Rad, MedGemma-1.5-4B, OctoMed, RadFM, DeepSeek-V4, llava-med-v1.5-mistral-7b, InternVL3.5-8B, and Lingshu-32B. The practical goal is to decide which models are worth spending GPU/endpoint time on first, without changing the official RadLE benchmark roster in `src/radle_benchmark.py`.

## Current State

Current state (2026-06-18 21:30 +05:30, Codex/GPT-5): Follow-up research changed the roadmap framing. For a world-facing comprehensive leaderboard, DeepSeek-VL2, RadFM, and LLaVA-Rad should be roadmap targets, not dismissed; they are just adapter/runtime-heavy compared with MedGemma, LLaVA-Med, and InternVL. OctoMed remains conditional pending a clearly usable checkpoint or endpoint. Next: hand back a phased leaderboard plan that separates "test now" from "must include eventually."

## Locked Facts

- Official RadLE execution remains `notebooks/RadLE_v1_5_Morning.ipynb` importing `src/radle_benchmark.py`.
- The official default `MODELS` roster must not be altered for this research task unless the user explicitly approves later.
- Generated outputs, local smoke CSVs, downloaded model files, and confidential images must not be committed.
- Existing experimental InternVL side path is `scripts/internvl_experimental_probe.py`.
- Consensus first broad search returned 20 papers and reported `tier: pro`, `papers_per_search: 20`.
- Current OpenRouter model metadata search found no exact matches for `medgemma`, `llava-med`, `llava`, `internvl`, `Lingshu`, `radfm`, or `DeepSeek-VL`.
- `google/medgemma-1.5-4b-it`, `microsoft/llava-med-v1.5-mistral-7b`, and `OpenGVLab/InternVL3_5-8B` have Hugging Face model cards with image-text-to-text support and vLLM/SGLang OpenAI-compatible serving examples.
- `google/medgemma-1.5-4b-it` access requires accepting Google's Health AI Developer Foundations terms on Hugging Face.
- LLaVA-Rad, RadFM, Lingshu, and OctoMed were verified primarily through papers/arXiv pages during this pass; immediately usable hosted model cards were not confirmed.
- DeepSeek-VL2 is the correct DeepSeek vision-language target for RadLE, not a text-only DeepSeek model name such as DeepSeek-V3/V4 unless a later official vision model is released.
- DeepSeek-VL2 has an official public GitHub repository at `deepseek-ai/DeepSeek-VL2`.
- RadFM has public GitHub repositories, including `chaoyi-wu/RadFM` and `MAGIC-AI4Med/RadFM`.
- LLaVA-Rad is 7B, radiology-specific, and the paper reports single-V100 feasibility, so it belongs in the leaderboard roadmap if weights/serving can be confirmed.
- RadFM has both arXiv and Nature Communications versions and explicitly targets 2D and 3D radiology data, so it is a high-value comprehensive-leaderboard candidate despite harder serving.

## Do Not Revisit

- Do not merge any candidate into the official full-run roster during this research pass. See Decision Log 2026-06-18.
- Do not run native big-three API comparisons for this task unless the user explicitly requests them. See prior InternVL plan.
- Do not treat a paper benchmark claim as sufficient for RadLE readiness; endpoint/runtime feasibility is a separate gate. See Decision Log 2026-06-18.

## Progress

- [x] (2026-06-18 20:40 +05:30, Codex/GPT-5) Read literature-review-helper, execplan skill, global PLANS.md, existing InternVL plan, and git status.
- [x] (2026-06-18 20:40 +05:30, Codex/GPT-5) Ran initial broad Consensus search for medical/radiology VLM candidates; received 20 results on Pro tier.
- [x] (2026-06-18 21:05 +05:30, Codex/GPT-5) Verified current source/model-card availability for each user-listed candidate using OpenRouter metadata, Hugging Face model cards, arXiv, and Consensus.
- [x] (2026-06-18 21:05 +05:30, Codex/GPT-5) Produced a ranked recommendation for RadLE experimental testing in the chat response.
- [x] (2026-06-18 21:30 +05:30, Codex/GPT-5) Ran deeper targeted Consensus and repository searches for DeepSeek-VL2, RadFM, OctoMed, and LLaVA-Rad after the user clarified the goal is a comprehensive world-facing leaderboard.

## Surprises & Discoveries

- Observation: The initial Consensus search surfaced Lingshu, LLaVA-Med, RadFound, CXR-LLAVA, and deployment-review papers, but not every exact user-listed name.
  Evidence: Consensus query `radiology medical vision-language model LLaVA-Rad MedGemma OctoMed RadFM Lingshu InternVL year:2023-2026` returned 20 papers.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: OpenRouter is not the route for these exact medical/open candidates today.
  Evidence: OpenRouter public model metadata was searched for `medgemma`, `llava-med`, `llava`, `internvl`, `Lingshu`, `radfm`, and `DeepSeek-VL`; no exact matches were found.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: DeepSeek-V4 is not the right named target for RadLE image benchmarking; DeepSeek-VL2 is the relevant DeepSeek vision-language family, but it is general-domain rather than medical/radiology-specific.
  Evidence: Searches surfaced DeepSeek-VL and DeepSeek-VL2 papers for image input; DeepSeek-V4 sources describe frontier LLM variants rather than a medical VLM path.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: DeepSeek-VL2 is significant enough for the leaderboard even though it is not medical-specific.
  Evidence: Consensus returned DeepSeek-VL2 with 555 citations and an official `deepseek-ai/DeepSeek-VL2` GitHub repo; the paper reports Tiny, Small, and full variants with 1.0B, 2.8B, and 4.5B activated parameters.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: RadFM is a high-priority radiology-specific benchmark target, not a low-priority curiosity.
  Evidence: Consensus returned the 2023 RadFM arXiv paper with 228 citations and a 2025 Nature Communications paper with 213 citations; GitHub search found public RadFM repos.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: OctoMed is promising but not yet in the same implementation-readiness bucket.
  Evidence: Consensus returned the 2025 OctoMed paper with 3 citations and no GitHub repository was found via repository search for `OctoMed Data Recipes multimodal medical reasoning`.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: LLaVA-Rad should be included if serving can be confirmed.
  Evidence: Web search found the 2024 arXiv paper "Towards a clinically accessible radiology foundation model..." describing LLaVA-Rad 7B, radiology training, and single-V100 inference feasibility.
  Date/Author: 2026-06-18, Codex/GPT-5.

## Decision Log

- Decision: Rank candidates by RadLE feasibility first, then likely scientific value.
  Rationale: A model that cannot be served with image input and RadLE-style JSON is not useful for the immediate benchmark, even if it has strong paper claims.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Keep this as a research memo plus plan update, not a source-code change.
  Rationale: The user asked for research, and the official benchmark roster must stay unchanged.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: For a public comprehensive leaderboard, maintain two categories: "runnable now" and "roadmap / adapter-needed", instead of excluding hard-to-serve models.
  Rationale: Scientific coverage and implementation readiness are different axes; excluding DeepSeek-VL2, RadFM, or LLaVA-Rad would weaken the leaderboard's credibility.
  Date/Author: 2026-06-18, Codex/GPT-5.

## Revision Notes

- v1 (2026-06-18, Codex/GPT-5): Initial research plan created after the user's model list and the broad Consensus reconnaissance search.

## Outcomes & Retrospective

Completed a first-pass and follow-up candidate triage. The practical recommendation is now split into phases: run MedGemma 1.5 4B, LLaVA-Med v1.5 Mistral 7B, and InternVL3.5 8B first; then add DeepSeek-VL2, LLaVA-Rad, and RadFM as adapter-needed but leaderboard-important models; then add Lingshu-32B and OctoMed once compute and checkpoint/endpoint readiness are clear. No reusable skill should be created; this is project-specific candidate triage.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Repo instructions require durable planning for multi-step analysis. | `manual` |
| Academic reconnaissance | `literature-review-helper` | The user asked for a research pass, and Consensus provides paper-grounded evidence. | `manual` |
| Model-card/deployment verification | `none` | Direct web/model-card checks are needed for current runtime feasibility. | `none` |
| Recommendation | `none` | Synthesis is project-specific. | `none` |

## Context And Orientation

RadLE is a radiology image benchmark whose official reusable logic lives in `src/radle_benchmark.py`. The current official roster has already been updated and pushed, and this research pass should not modify it. Candidate models should be evaluated as separate experimental endpoints or scripts until their image-input behavior, JSON compliance, runtime cost, and stability are proven on 1 case and then 3-5 cases.

## Plan Of Work

For each model family, collect: paper/model-card source, modality support, parameter size, likely runtime requirement, OpenAI-compatible serving feasibility, medical/radiology specificity, and expected integration risk. Then rank into tiers:

- Tier A: test first on GCP credits with minimal custom plumbing.
- Tier B: scientifically relevant but higher runtime or integration risk.
- Tier C: hold until clearer availability or endpoint support.

## Validation And Acceptance

Acceptance is a sourced, practical recommendation that names which candidate to test first, which to avoid for now, and what endpoint/runtime path each viable candidate needs. No source changes are required.
