# RadLE agent instructions

## Git and Colab discipline

All code and notebook edits must happen in the local repository, be committed and pushed to Git, and reach Colab by refreshing/opening the published notebook release. Browser/computer use may only open, refresh, run, stop gracefully, or monitor Colab. Never type, paste, replace, or patch code cells through Chrome, including temporary loader wrappers.

Keep notebooks/RadLE_v1_5_Morning.ipynb and its Python modules aligned in one immutable Git release. Preserve the four-cell setup, client/import, configuration, and autonomous-workflow structure. Cell 4 calls run_autonomous_openrouter_workflow; do not replace it with direct collector or exec wrappers. Runtime fixes belong in Python and the canonical notebook.

Before a refresh or restart, inspect the dashboard, let active calls drain, and preserve Drive CSVs, backups, migration receipts and journal. Keep the run label, cohort, prompt, images, provider/privacy/reasoning settings and attempt limits unchanged unless the user authorizes a change. No automatic third attempt, scoring, promotion or public export.

Every delegation must include these restrictions, the exact Git release, run label and latest verified state. Monitoring is read-only by default. On mismatch or uncertain remote outcome, report it; never patch the notebook in the browser. Read Documents/execplan_restore_colab_workflow_20261008.md on handoff or context compaction.

## ExecPlans

Use an ExecPlan for multi-step analyses or significant changes; keep it under Documents/.
