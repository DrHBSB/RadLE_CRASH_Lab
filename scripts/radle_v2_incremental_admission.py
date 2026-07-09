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
from radle_incremental_admission import prepare_incremental_admission, project_one_model_package


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


def _cmd_prepare(args: argparse.Namespace) -> int:
    receipt = prepare_incremental_admission(
        parent_wide=Path(args.parent_wide),
        parent_final_long_master=Path(args.parent_final_long_master),
        parent_authority_manifest=Path(args.parent_authority_manifest),
        incoming_package=Path(args.incoming_package),
        model_key=args.model_key,
        roster_path=Path(args.roster),
        variants_path=Path(args.variants),
        states_path=Path(args.states),
        output_root=Path(args.output_root),
        repo_root=REPO_ROOT,
        dry_run=args.dry_run,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"INTAKE_ID={receipt['intake_id']}")
    if receipt.get("staging_root"):
        print(f"STAGING_ROOT={receipt['staging_root']}")
    print(f"TRANSACTION_STATE={receipt['transaction_state']}")
    return 0


def _cmd_project_one_model(args: argparse.Namespace) -> int:
    receipt = project_one_model_package(
        source_wide=Path(args.source_wide),
        model_key=args.model_key,
        output_package=Path(args.output_package),
        dry_run=args.dry_run,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"PROJECTION_ID={receipt['projection_id']}")
    if receipt.get("output_package"):
        print(f"OUTPUT_PACKAGE={receipt['output_package']}")
    print(f"PROJECTION_STATE={receipt['projection_state']}")
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

    prepare = subparsers.add_parser("prepare", help="validate and stage one incremental model admission")
    prepare.add_argument("--parent-wide", required=True)
    prepare.add_argument("--parent-final-long-master", required=True)
    prepare.add_argument("--parent-authority-manifest", required=True)
    prepare.add_argument("--incoming-package", required=True)
    prepare.add_argument("--model-key", required=True)
    prepare.add_argument("--roster", required=True)
    prepare.add_argument("--variants", required=True)
    prepare.add_argument("--states", default="config/radle_v2_terminal_states.json")
    prepare.add_argument("--output-root", required=True)
    prepare.add_argument("--dry-run", action="store_true")
    prepare.set_defaults(func=_cmd_prepare)

    project = subparsers.add_parser("project-one-model", help="project a shared wide result into one model package")
    project.add_argument("--source-wide", required=True)
    project.add_argument("--model-key", required=True)
    project.add_argument("--output-package", required=True)
    project.add_argument("--dry-run", action="store_true")
    project.set_defaults(func=_cmd_project_one_model)
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
