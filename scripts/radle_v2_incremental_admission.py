from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from radle_incremental_admission import ValidationError, sha256_file, validate_configs


def _cmd_check_config(args: argparse.Namespace) -> int:
    receipt = validate_configs(
        roster_path=Path(args.roster),
        judges_path=Path(args.judges),
        states_path=Path(args.states),
        fixture_csv=Path(args.fixture) if args.fixture else None,
        repo_root=REPO_ROOT,
    )
    receipt["config_hashes"] = {
        "roster": sha256_file(Path(args.roster)),
        "judges": sha256_file(Path(args.judges)),
        "states": sha256_file(Path(args.states)),
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("CONFIG_RESULT=PASS")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RadLE v2 incremental admission utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_config = subparsers.add_parser("check-config", help="validate roster, judge, and terminal-state configs")
    check_config.add_argument("--roster", required=True)
    check_config.add_argument("--judges", required=True)
    check_config.add_argument("--states", required=True)
    check_config.add_argument("--fixture", default="tests/fixtures/radle_incremental_admission/unit_cases.csv")
    check_config.set_defaults(func=_cmd_check_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValidationError as exc:
        print(f"CONFIG_RESULT=FAIL {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
