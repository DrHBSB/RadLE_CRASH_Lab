from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from radle_incremental_admission import ValidationError, run_synthetic_dual_judge_delta
from radle_openrouter_judge import run_openrouter_dual_judge_delta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RadLE v2 dual-judge delta adjudication")
    parser.add_argument("--staging-root", required=True)
    parser.add_argument("--config", default="config/radle_v2_judges.json")
    parser.add_argument("--out-dir")
    parser.add_argument("--authorization", help="paid_judge_authorization.json path for --real")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--synthetic", action="store_true", help="write deterministic local synthetic judge evidence")
    modes.add_argument("--real", action="store_true", help="run authorization-gated OpenRouter judging")
    args = parser.parse_args(argv)

    staging_root = Path(args.staging_root)
    out_dir = Path(args.out_dir) if args.out_dir else staging_root / "judge_evidence"
    try:
        if args.synthetic:
            receipt = run_synthetic_dual_judge_delta(
                staging_root=staging_root,
                judges_path=Path(args.config),
                out_dir=out_dir,
                repo_root=REPO_ROOT,
                dry_run=False,
            )
        else:
            authorization_path = Path(args.authorization) if args.authorization else None
            receipt = run_openrouter_dual_judge_delta(
                staging_root=staging_root,
                judges_path=Path(args.config),
                out_dir=out_dir,
                repo_root=REPO_ROOT,
                authorization_path=authorization_path,
                dry_run=not args.real,
            )
    except ValidationError as exc:
        print(f"JUDGE_RESULT=FAIL {exc}", file=sys.stderr)
        return 2

    print(json.dumps(receipt, indent=2, sort_keys=True))
    if not args.synthetic and not args.real:
        print("JUDGE_RESULT=DRY_RUN_VALIDATED")
    else:
        print("JUDGE_RESULT=PASS")
        print(f"JUDGE_EVIDENCE_DIR={out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
