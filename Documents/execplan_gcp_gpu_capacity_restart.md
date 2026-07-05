# Restart RadLE Workbench GPU Capacity Hunt

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. The repo has no local `PLANS.md` and no repo-local `AGENTS.md`; the active project instruction was provided in chat and says to use ExecPlans for complex multi-step work and prefer `Documents/`.

## Purpose / Big Picture

RadLE needs a safe restart path for hunting scarce GCP GPU capacity for the medical Workbench runtime without accidentally creating duplicate billable Colab/Workbench environments or deleting valuable prior resources. The user can see this working by running the preflight command, confirming no valuable existing resources are present, then explicitly approving the `-Execute` command. The script stops creating as soon as Workbench enters a provisioning state and then monitors until the instance is actually usable.

## Current State

Current state (2026-07-03 04:30 IST, Codex/GPT-5): The better-machine hunt is stopped and the A100 40GB Workbench instance `radle-pro-a100-0703033955-7553` in `us-west4-b` remains the active working machine. The prior 2x L4 Workbench instance `medical-master-radfm` was archived through JupyterLab to `gs://radle-medical-data-toronto/backups/medical-master-radfm_nondataset_20260702_224442.tar.gz` and then stopped again; Workbench reports `STOPPED` and Compute reports `TERMINATED`. The shared stop file `outputs/gcp_hunt/STOP_ALL_HUNTS` remains present and no hunter PowerShell processes remain. Next: only delete `medical-master-radfm` after the user explicitly approves deletion, since the archive and stopped state have been verified.

## Locked Facts

- Project is `crashlab-synthetic`.
- Previous successful resource was Workbench instance `medical-master-radfm`, not Colab.
- Previous successful zone was `northamerica-northeast2-b`.
- Previous successful shape was `g2-standard-24`, `2 x NVIDIA_L4`, `200GB PD_BALANCED`.
- Cloud Assist reported on 2026-07-03 that `medical-master-radfm` is currently active in `northamerica-northeast2-b` and consuming `2 x NVIDIA_L4`; verify locally with `gcloud workbench instances describe` before any live hunt.
- Current Workbench evidence shows Lingshu-32B Q8 can run on the existing 2x L4 machine when wrapped as `lingshu-32b-8k`; the raw model at larger context OOMed, but the derived 8k model completed the five-case image probe with distinct outputs.
- For Lingshu multi-JSON outputs, final abstention counts because `extract_json_safely` takes the last valid JSON object; run Lingshu through the standard raw -> audit -> promote path with no special adjudication sidecar for commit-then-abstain cases.
- Live hunt on 2026-07-03 landed Workbench instance `radle-pro-a100-0703033955-7553` in `us-west4-b`, shape `a2-highgpu-1g`, `1 x NVIDIA_TESLA_A100`, state `ACTIVE`, proxy URI `30eea78891bde21a-dot-us-west4.notebooks.googleusercontent.com`.
- `medical-master-radfm` non-dataset backup archive exists at `gs://radle-medical-data-toronto/backups/medical-master-radfm_nondataset_20260702_224442.tar.gz`, size `8004985` bytes / `7.63MiB`, created `2026-07-02T22:44:47Z`.
- After the archive, `medical-master-radfm` was stopped again; Workbench state is `STOPPED` and Compute state is `TERMINATED`.
- The L4 quad attempt `radle-beast-l4-0703034122-4589` in `europe-west6-b` is not currently a live resource: Workbench describe returned `NOT_FOUND`, Compute describe returned `NOT_FOUND`, and no matching disk was listed.
- `outputs/gcp_hunt/STOP_ALL_HUNTS` is intentionally present after the live hunt and must not be removed unless the user intentionally restarts hunting.
- The dual hunter scripts now include `--quiet` on Workbench create and a top-level `FATAL_UNHANDLED_EXCEPTION` log catch to avoid silent hidden-process exits on future restarts.
- A100 80GB/H100 are excluded from the live hunt because Cloud Assist reported zero quota.
- Primary target is now `g2-standard-48` with `4 x NVIDIA_L4`; secondary target is `a2-highgpu-1g` with `1 x NVIDIA_TESLA_A100`.
- Live L4 quad zones exclude `me-central2-a` and `me-central2-c` despite technical L4 support because prior project logs showed `LOCATION_POLICY_VIOLATED` for `me-central2`.
- Workbench create commands should use `--install-gpu-driver`, `--vm-image-project=cloud-notebooks-managed`, and `--vm-image-family=workbench-instances`; do not use manual `--metadata=install-nvidia-driver=True`.
- GPU quota metrics are `NVIDIA_L4_GPUS` for G2/L4 and `NVIDIA_A100_GPUS` for A2/A100; CPU preflight should consider `CPUS` plus family metrics if visible (`G2_CPUS` or `A2_CPUS`).
- Workbench failure classification should distinguish quota (`QUOTA_EXCEEDED`, quota metric strings), stockout (`ZONE_RESOURCE_POOL_EXHAUSTED*`, not enough resources, out of stock), unsupported shape (`INVALID_FIELD_VALUE`, unsupported machine/accelerator strings), location policy (`LOCATION_POLICY_VIOLATED`, `constraints/gcp.resourceLocations`, org policy strings), and transient API/rate limit (`429`, `RATE_LIMIT_EXCEEDED`, `Too many requests`, `503`).
- For generated attempts, automatic deletion is limited to exact current attempts in `FAILED` or `DELETED`; `STOPPING`, `STOPPED`, and `ERROR` now force manual inspection.
- PowerShell plus `gcloud` is preferred because it reuses existing local `gcloud` auth.
- Cloud Assist's `google-cloud-colab` Python package suggestion was a hallucination and should not be revived.
- Colab Enterprise super-hunt should stop if Workbench lands to avoid duplicate billing.

## Do Not Revisit

- Do not restart `scratch/poll_colab_2xl4.ps1`; it uses a static runtime name and treats `CREATING` as success. See Decision Log 2026-07-02.
- Do not use `scratch/poll_gcp_instances.ps1` for this restart; it is a four-model 1x L4/A100 fanout and misses the target shape. See Decision Log 2026-07-02.
- Do not delete `medical-master-radfm`, `medical-test-l4`, or `medical-master-a100` from an automated cleanup loop. See Decision Log 2026-07-02.
- Do not run naive independent loops without a shared stop file; double success can become a billing trap. See Decision Log 2026-07-03.

## Progress

- [x] (2026-07-02 22:10 IST, Codex/GPT-5) Read the Cloud Assist transcript at `C:\Users\thehb\.codex\attachments\fd1a3f89-46e4-4724-af3c-a799dafed9fc\pasted-text.txt`.
- [x] (2026-07-02 22:15 IST, Codex/GPT-5) Read Antigravity `implementation_plan.md`, `gpu_locations.md`, and required `scratch/*.ps1` scripts.
- [x] (2026-07-02 22:20 IST, Codex/GPT-5 + explorer subagents) Split read-only reviews across Workbench, Colab/duplicate-hunt, and quota/cleanup angles.
- [x] (2026-07-02 22:26 IST, Codex/GPT-5) Drafted guarded restart script under `scripts/hunt_workbench_radfm_2xl4.ps1`.
- [x] (2026-07-02 22:26 IST, Codex/GPT-5) Run preflight only after user approval; completed for the dual A100/L4 hunters on 2026-07-03 after explicit user approval.
- [x] (2026-07-02 22:26 IST, Codex/GPT-5) Run live hunt only after explicit user approval; completed for the dual A100/L4 hunters on 2026-07-03 after the user said to start the script.
- [x] (2026-07-03 00:00 IST, Codex/GPT-5) Drafted two separate guarded hunters with a shared stop file: `scripts/radle-beast-l4-hunt.ps1` and `scripts/radle-pro-a100-hunt.ps1`.
- [x] (2026-07-03 02:30 IST, Codex/GPT-5) Assimilated Cloud Assist location/quota/flag guidance into the ExecPlan and patched both hunter zone lists.
- [x] (2026-07-03 02:35 IST, Codex/GPT-5) Assimilated Cloud Assist failure-classification and backoff guidance into both hunter scripts.
- [x] (2026-07-03 03:01 IST, Codex/GPT-5) Recorded Cloud Assist script review and current-environment report; no local preflight or create command has been run.
- [x] (2026-07-03 03:10 IST, Codex/GPT-5) Recorded pasted Workbench evidence that Lingshu Q8 works on current 2x L4 with an 8k derived Ollama model and vision-path probe outputs differ by image.
- [x] (2026-07-03 03:35 IST, Codex/GPT-5) Ran dual preflights; both A100 40GB and L4 quad preflights completed without quota/access blockers and created no resources.
- [x] (2026-07-03 03:38 IST, Codex/GPT-5) Started live hidden PowerShell hunters: L4 PID `50580`, log `outputs/gcp_hunt/l4quad_live_20260703_033824.log`; A100 PID `62540`, log `outputs/gcp_hunt/a100_40_live_20260703_033824.log`.
- [x] (2026-07-03 03:42 IST, Codex/GPT-5) Detected A100 Workbench landed in `PROVISIONING` and an L4 quad attempt briefly in `INITIALIZING`; wrote a manual `STOP_ALL_HUNTS` file and verified no hunter PowerShell processes remained.
- [x] (2026-07-03 03:44 IST, Codex/GPT-5) Verified A100 Workbench `radle-pro-a100-0703033955-7553` reached `ACTIVE` with proxy URI; verified the L4 attempt was no longer present in Workbench, Compute, or disks.
- [x] (2026-07-03 03:45 IST, Codex/GPT-5) Patched both live hunter scripts with `--quiet` on create and a top-level fatal-error logger; PowerShell parser validation passed for both scripts.
- [x] (2026-07-03 04:29 IST, Codex/GPT-5) Verified the user-created non-dataset archive for `medical-master-radfm` in GCS, then stopped `medical-master-radfm`; final checks show Workbench `STOPPED`, Compute `TERMINATED`, and A100 `RUNNING`.

## Surprises & Discoveries

- Observation: The old Workbench-adjacent logs show `gcloud workbench instances list --filter="name:..."` warning that `name` was not present, so the restart script uses exact `instances describe <name> --location=<zone>` instead of list filters for candidate state checks.
  Evidence: Antigravity `task-799.log` repeatedly printed `WARNING: The following filter keys were not present in any resource : name`.
  Date/Author: 2026-07-02, Codex/GPT-5

- Observation: The Colab super-hunt logs created async runtime IDs and then polled blank states. Blank Colab state should be treated as unknown, not success or clean failure.
  Evidence: Antigravity `task-799.log` and `task-825.log` show `Current Status (...):` with no state after create operations.
  Date/Author: 2026-07-02, Codex/GPT-5 and Newton explorer

- Observation: The current `medical-master-radfm` machine can load Lingshu-32B Q8 across both L4 GPUs, but the raw model/context path can OOM for image probes.
  Evidence: Pasted Workbench logs show Ollama offloaded 64/65 layers with CUDA0/CUDA1 buffers, then raw probe requests failed with CUDA OOM; after creating `lingshu-32b-8k`, five probe cases completed with distinct outputs.
  Date/Author: 2026-07-03, Codex/GPT-5

- Observation: The hidden live hunter processes exited immediately after logging their first create attempts, before writing normal create-output or post-create classifier lines.
  Evidence: `outputs/gcp_hunt/a100_40_live_20260703_033824.log` ends at `Attempting create` for `radle-pro-a100-0703033955-7553`; direct `gcloud workbench instances describe` showed the instance existed and later became `ACTIVE`. The L4 log likewise ended at `Attempting create`; the candidate briefly described as `INITIALIZING`, then disappeared cleanly.
  Date/Author: 2026-07-03, Codex/GPT-5

## Decision Log

- Decision: Reuse and patch the logic from `scratch/poll_radfm_2xl4.ps1`, not the broader multi-model or Colab scripts.
  Rationale: It exactly matches the historical successful Workbench resource name, shape, disk, accelerator, and stop-hunt states.
  Date/Author: 2026-07-02, Codex/GPT-5

- Decision: The proposed script blocks on any existing critical Workbench resource before creating anything.
  Rationale: The user explicitly warned to check whether `medical-master-radfm`, `medical-test-l4`, or `medical-master-a100` are valuable before destructive cleanup; blocking also avoids quota/billing surprises.
  Date/Author: 2026-07-02, Codex/GPT-5

- Decision: Keep automatic cleanup only for the exact current Workbench attempt after it reaches a terminal failed state.
  Rationale: This preserves the ghost-resource blunder save without deleting resources that predate the current run.
  Date/Author: 2026-07-02, Codex/GPT-5

- Decision: Workbench `PROVISIONING`, `STARTING`, `INITIALIZING`, `STAGING`, or `ACTIVE` stops the hunt, then the script verifies until `ACTIVE` with a `proxyUri`.
  Rationale: Workbench can be considered landed before it is usable; further creation attempts must stop to avoid duplicates.
  Date/Author: 2026-07-02, Codex/GPT-5

- Decision: Use two separate scripts for 4x L4 and A100 40GB, but make them share `outputs/gcp_hunt/STOP_ALL_HUNTS`.
  Rationale: Separate loops increase scheduler attempts against different hardware pools; the shared stop file prevents silent duplicate creation after either profile lands.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Preserve `--install-gpu-driver` from the known-working Workbench script, while also setting the explicit Workbench VM image family that Cloud Assist recommended.
  Rationale: `--install-gpu-driver` is the documented Workbench flag in the local `gcloud` help and was used in the successful L4 script.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Exclude `me-central2` from the live L4 quad hunter even though it appears in the support list.
  Rationale: Cloud Assist says the prior `LOCATION_POLICY_VIOLATED` implies a region-level project/org restriction inherited by the zones.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Expand the live zone arrays to the Cloud Assist supported-zone lists rather than only high-density shortlist zones.
  Rationale: The immediate objective is capacity landing; randomized broader zones give more scheduler attempts while quota/access preflight screens obvious blockers.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Add bounded exponential backoff with jitter only for transient API/rate-limit failures.
  Rationale: 429/503 errors are control-plane pressure, not stockout; retrying the same create command a few times avoids false stockout classification while preventing infinite API hammering.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Delete only generated attempts that reach `FAILED` or `DELETED`; stop for manual inspection on `STOPPING`, `STOPPED`, or `ERROR`.
  Rationale: Cloud Assist identified `FAILED`/`DELETED` as safe terminal cleanup states; the other states may represent in-progress or ambiguous resources.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Treat Cloud Assist's `medical-master-radfm` active-instance report as a preflight verification target, not as final local truth.
  Rationale: The user wants decisions grounded in current machine/project evidence; preflight should confirm the Workbench instance state, shape, and proxy before live hunting.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Do not start live capacity hunting while the current 2x L4 machine is producing usable Lingshu probe evidence unless the user explicitly prioritizes RadFM or higher headroom over immediate Lingshu shakedown.
  Rationale: The existing machine may already cover the Lingshu path; creating a new machine before finishing the current shakedown increases cost and context switching.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: For Lingshu commit-then-abstain multi-JSON outputs, keep the standard extractor's take-last semantics and count the final abstention.
  Rationale: `extract_json_safely` already returns `valid[-1]`, and the Lingshu runner documents the radiologist/user ruling that the model's final word counts; changing to take-first would create a model-specific exception and require sidecar adjudication.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: After the live hunt landed A100 and transient L4 candidates, write the shared stop file manually and do not delete any GPU Workbench resource automatically.
  Rationale: A100 was already a valid improvement target, while the L4 candidate needed verification and later proved to have rolled back; deletion decisions are billable/destructive and should remain user-approved.
  Date/Author: 2026-07-03, Codex/GPT-5

- Decision: Patch both live hunter scripts with `--quiet` on create plus a top-level fatal-error logger.
  Rationale: Hidden PowerShell launches should never exit silently after a resource create attempt; future runs need log evidence for any unhandled exception or prompt-related failure.
  Date/Author: 2026-07-03, Codex/GPT-5

## Revision Notes

- v1 (2026-07-02, Codex/GPT-5): Created a restart plan and guarded script from the prior artifacts, with no cloud resource creation.
- v2 (2026-07-03, Codex/GPT-5): Added two separate guarded hunter scripts for the Cloud Assist A100/L4 pivot and recorded the shared stop-file policy.
- v3 (2026-07-03, Codex/GPT-5): Assimilated Cloud Assist zone, quota, and Workbench flag guidance; patched scripts to broaden zones and exclude `me-central2`.
- v4 (2026-07-03, Codex/GPT-5): Assimilated Cloud Assist failure-classification and transient backoff guidance; tightened automatic cleanup states.
- v5 (2026-07-03, Codex/GPT-5): Recorded Cloud Assist's review approval and reported active `medical-master-radfm` context as a local preflight verification target.
- v6 (2026-07-03, Codex/GPT-5): Recorded current-machine Lingshu 8k success evidence and paused live-hunt posture pending user direction.
- v7 (2026-07-03, Codex/GPT-5): Recorded the Lingshu final-abstention-counts ruling and standard raw-audit-promote path.
- v8 (2026-07-03, Codex/GPT-5): Recorded user-approved live hunt, A100 landing, L4 rollback, manual stop-file state, and script hardening after silent hidden-process exits.

## Outcomes & Retrospective

Live hunt milestone achieved. The A100 40GB Workbench target landed as `radle-pro-a100-0703033955-7553` in `us-west4-b` and reached `ACTIVE` with proxy URI `30eea78891bde21a-dot-us-west4.notebooks.googleusercontent.com`. The L4 quad attempt did not persist and showed no live Workbench, Compute, or disk residue on follow-up checks. No Colab duplicate-hunt cleanup was needed. No reusable global skill lesson should be promoted without user approval; the project-specific lesson is already recorded here and in the patched scripts.

Archive-before-delete checkpoint also achieved. The prior 2x L4 machine `medical-master-radfm` has a non-dataset backup in GCS and has been stopped again, so GPU billing for that machine should be off while its disks remain recoverable until explicit deletion.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | The task is multi-step, stateful, and cloud-cost sensitive. | `auto-suggest` |
| Artifact review | `none` | Local file and log inspection is sufficient. | `none` |
| Live preflight | `none` | Use guarded `gcloud` read commands only. | `none` |
| Live hunt | `none` | Use the approved PowerShell script directly. | `none` |
| Review before cleanup | `goal-judge` or equivalent skeptical review | Useful if a valuable existing resource is found and deletion is being considered. | `manual` |

## Context And Orientation

The prior Antigravity folder is `C:\Users\thehb\.gemini\antigravity-ide\brain\62cb0beb-6eed-4a99-afa7-0bf8b50eb1b8\`. The important historical script is `scratch/poll_radfm_2xl4.ps1`; it won a Workbench instance in `northamerica-northeast2-b` according to `.system_generated\tasks\task-823.log`. The Colab scripts are secondary and should be stopped once Workbench lands.

## Plan Of Work

Keep the restart local to the existing checkout. No branch or worktree is required for this proposal-only artifact. If the user approves running the hunt, run the preflight first, inspect any existing critical resources, then run the live command only if the preflight is clean.

## Concrete Steps (Commands)

From `C:\Users\thehb\Documents\RadLE v2`, dry-run/preflight the 4x L4 hunter:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\thehb\Documents\RadLE v2\scripts\radle-beast-l4-hunt.ps1" -PreflightOnly

Dry-run/preflight the A100 40GB hunter:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\thehb\Documents\RadLE v2\scripts\radle-pro-a100-hunt.ps1" -PreflightOnly

The older 2x L4 script remains available as a fallback only:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\thehb\Documents\RadLE v2\scripts\hunt_workbench_radfm_2xl4.ps1" -PreflightOnly

Expected success shape:

    DRY RUN ONLY. No resources were created. Re-run with -Execute to start this hunter.

Start the live 4x L4 Workbench hunt only after explicit approval:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\thehb\Documents\RadLE v2\scripts\radle-beast-l4-hunt.ps1" -Execute

Start the live A100 40GB Workbench hunt only after explicit approval:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\thehb\Documents\RadLE v2\scripts\radle-pro-a100-hunt.ps1" -Execute

Both scripts share this stop file:

    C:\Users\thehb\Documents\RadLE v2\outputs\gcp_hunt\STOP_ALL_HUNTS

Expected stop-hunt shape:

    SUCCESS_STOP_HUNT: <generated-name> reached PROVISIONING in <zone>.
    Verification state: zone=<zone> state=ACTIVE proxyUri=<uri>
    USABLE: <generated-name> is ACTIVE in <zone> with proxyUri=<uri>

## Validation And Acceptance

The script is acceptable when it refuses to create without `-Execute`, runs preflight read checks, randomizes the curated L4 zone list, classifies quota/access failures separately from stockout, stops on Workbench provisioning states, and monitors until `ACTIVE` with a proxy URI. The script is not acceptable if it starts Colab, creates resources in dry-run mode, treats Colab `CREATING` as success, or deletes any pre-existing critical Workbench resource.

## Idempotence And Recovery

Running without `-Execute` is safe and creates only a local log file under `outputs/gcp_hunt/`. Running with `-PreflightOnly` is read-only against GCP. Running with `-Execute` creates at most one Workbench attempt at a time and deletes only the exact current failed attempt after terminal failed states. If the script stops on `UNKNOWN_STATE`, inspect the named instance and zone manually before restarting.

## Artifacts And Notes

Key prior proof from Antigravity `task-823.log`:

    Trying 2x L4 in northamerica-northeast2-b...
    Create in progress for workbench instance medical-master-radfm [...]
    SUCCESS! medical-master-radfm is provisioning in northamerica-northeast2-b!

## Interfaces And Dependencies

Required local command: `gcloud`. Required enabled APIs: `compute.googleapis.com`, `notebooks.googleapis.com`, and `aiplatform.googleapis.com`. The script uses Workbench v2 CLI commands through `gcloud workbench instances create|describe|delete` and Compute quota reads through `gcloud compute regions describe`.
