from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from radle_incremental_admission import ValidationError, audit_prepared_staging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit RadLE v2 incremental admission artifacts")
    parser.add_argument("--admission-root", required=True)
    parser.add_argument("--phase", choices=["prepared"], required=True)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.phase == "prepared":
            receipt = audit_prepared_staging(Path(args.admission_root))
        else:
            raise ValidationError(f"unsupported audit phase: {args.phase}")
    except ValidationError as exc:
        print(f"RESULT=FAIL {exc}", file=sys.stderr)
        return 2

    receipt["no_write"] = bool(args.no_write)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
