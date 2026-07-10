#!/usr/bin/env python3
"""RadLE v2 finalization (built incrementally, one step per commit).

STEP 1 (this commit): fix human role labels in the authoritative master and add
seniority columns. No summaries, no audit, no other files are touched.

Master: outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/
        radle_v2_final_long_master.csv

Role/seniority is keyed by person name (the `provider` column for human rows), so
the remap is deterministic and safe to re-apply (idempotent).
"""
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:/Users/thehb/Documents/RadLE v2")
OUT = ROOT / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
MASTER = OUT / "radle_v2_final_long_master.csv"
BACKUP = Path(
    r"C:/Users/thehb/AppData/Local/Temp/claude/"
    r"C--Users-thehb-Documents-RadLE-v2/5ad141d4-072f-4c1e-8a58-f0f572281fa9/scratchpad"
)

# person name -> (seniority text, ordinal rank 1..7).  rank<=2 => Trainee (PGY
# resident), rank>=3 => Radiologist (board-certified).  7 Radiologists, 5 Trainees.
SENIORITY = {
    "Nishtha Mahajan": ("PGY2", 1),
    "Unnathi Nayak": ("PGY2", 1),
    "Devyani Singh": ("PGY3", 2),
    "Shravan Reddy": ("PGY3", 2),
    "Dhanush Jayanna": ("PGY3", 2),
    "Prerna Priyadarshini": ("6mo post-MD", 3),
    "Prathamesh Tadage": ("PGY3", 2),
    "Rahul John Joseph": ("2y post-MD", 4),
    "Vikas H P": ("3y post-MD", 5),
    "Yash Jakhotia": ("3y post-MD", 5),
    "Manish Kumar Jha": ("4y post-MD", 6),
    "Rajesh Vanagundi": ("7y post-MD", 7),
}


def role_for(rank: int) -> str:
    return "Trainee" if rank <= 2 else "Radiologist"


def main():
    shutil.copy2(MASTER, BACKUP / "radle_v2_final_long_master.step1_pre.csv")

    m = pd.read_csv(MASTER)
    assert len(m) == 6000, f"expected 6000 rows, got {len(m)}"
    assert m.duplicated(["Master_Case_ID", "model_blinded"]).sum() == 0

    hmask = m.domain == "human"
    # roster must exactly match the 12 human persons present in the master
    present = set(m.loc[hmask, "provider"].unique())
    assert present == set(SENIORITY), f"roster mismatch: {present ^ set(SENIORITY)}"

    m["rater_seniority"] = pd.NA
    m["rater_seniority_rank"] = pd.NA
    changes = {}
    for name, (stext, rank) in SENIORITY.items():
        rows = hmask & (m.provider == name)
        assert rows.sum() == 200, f"{name}: expected 200 rows, got {int(rows.sum())}"
        old = m.loc[rows, "candidate"].iloc[0]
        new = role_for(rank)
        if old != new:
            changes[name] = f"{old} -> {new}"
        m.loc[rows, "candidate"] = new
        m.loc[rows, "rater_seniority"] = stext
        m.loc[rows, "rater_seniority_rank"] = rank

    m.to_csv(MASTER, index=False)

    print("candidate value changes:", changes or "(none)")
    hs = m[m.domain == "human"]
    print("role -> #people:", hs.groupby("candidate")["provider"].nunique().to_dict())
    print("rows per role:", hs.candidate.value_counts().to_dict())
    print(
        "seniority tiers:",
        hs.drop_duplicates("provider")
        .groupby(["rater_seniority_rank", "candidate"])["rater_seniority"]
        .agg(lambda s: s.iloc[0])
        .to_dict(),
    )
    print("AI rows have blank seniority:", m[m.domain != "human"].rater_seniority.isna().all())
    print("new columns:", [c for c in m.columns if c.startswith("rater_")])
    print("total columns:", len(m.columns))


if __name__ == "__main__":
    main()
