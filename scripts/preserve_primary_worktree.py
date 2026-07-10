from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


EXCLUDED_PATHS = {
    ".claude/settings.local.json",
    "Documents/execplan_radle_v2_incremental_model_admission.md",
    "src/radle_benchmark.py",
    "src/radle_meta_model_api_runtime.py",
}

OVERLAP_PATHS_TO_PRESERVE = {
    "README.md",
    "Documents/execplan_medical_custom_runtime_colab.md",
    "Documents/execplan_medical_workbench_runtime.md",
    "notebooks/RadLE_Medical_Custom_Runtime.ipynb",
    "notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb",
    "notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb",
    "notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb",
    "notebooks/RadLE_Medical_Workbench_Runtime.ipynb",
    "notebooks/RadLE_v1_5_Morning.ipynb",
    "scripts/radle_v2_finalize_summaries.py",
    "scripts/summary_human.py",
    "scripts/write_audit.py",
}

PANEL_EXPERIMENT_MARKERS = (
    "contact_sheet",
    "palette_options",
    "color_variants",
    "gap_arrow_options",
    "blue_likert",
    "category_palette",
    "model_bar_color",
    "claude_octomed_bar_color",
)


def run_git(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_status(root: Path) -> dict[str, str]:
    raw = run_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = raw.split(b"\0")
    result: dict[str, str] = {}
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2].decode("ascii")
        path = entry[3:].decode("utf-8", errors="surrogateescape").replace("\\", "/")
        if status[0] in {"R", "C"}:
            if index >= len(entries) or not entries[index]:
                raise RuntimeError(f"missing rename source for {path}")
            index += 1
        result[path] = status
    return result


def parse_index(root: Path) -> dict[str, str]:
    raw = run_git(root, "ls-files", "--stage", "-z")
    result: dict[str, str] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, path_raw = entry.split(b"\t", 1)
        _mode, blob, stage = metadata.decode("ascii").split()
        if stage == "0":
            result[path_raw.decode("utf-8", errors="surrogateescape").replace("\\", "/")] = blob
    return result


def tracked_paths(root: Path) -> set[str]:
    raw = run_git(root, "ls-tree", "-r", "-z", "--name-only", "HEAD")
    return {
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in raw.split(b"\0")
        if value
    }


def classification(path: str) -> str:
    lower = path.lower()
    if any(marker in lower for marker in PANEL_EXPERIMENT_MARKERS):
        return "panel_experiments_docs"
    if path.startswith("scripts/assets/"):
        return "panel_core_assets"
    if path.startswith("scripts/reference/radle_stats_handwritten_svg_panels/"):
        return "panel_core_assets"
    if path.startswith("scripts/") and any(
        token in lower
        for token in (
            "score1000",
            "handwritten_panels",
            "handwritten_svg_panels",
            "handwritten_stats",
            "clean_adjudication_master",
            "temp_final_scoring",
        )
    ):
        return "panel_core_assets"
    if path.startswith("Documents/") and any(
        token in lower for token in ("handwritten", "score1000", "score2000", "temp_final_scoring")
    ):
        return "panel_experiments_docs"
    return "runtime_document_changes"


def build_manifest(source: Path, destination: Path, incremental: Path) -> dict[str, object]:
    statuses = parse_status(source)
    # Git's global-excludes visibility differs between the parent PowerShell
    # process and Python subprocesses on this workstation. Force explicitly
    # excluded local settings into the inventory when the file exists.
    for excluded in EXCLUDED_PATHS:
        if (source / Path(excluded)).is_file() and excluded not in statuses:
            statuses[excluded] = "??"
    index = parse_index(source)
    incremental_paths = tracked_paths(incremental)
    primary_only = sorted(path for path in statuses if path not in incremental_paths)
    selected = sorted(
        (set(primary_only) | (set(statuses) & OVERLAP_PATHS_TO_PRESERVE)) - EXCLUDED_PATHS
    )

    entries: list[dict[str, object]] = []
    for relative in selected:
        source_path = source / Path(relative)
        if not source_path.is_file():
            raise RuntimeError(f"selected source path is not a file: {source_path}")
        working_hash = sha256_file(source_path)
        staged_blob = index.get(relative)
        staged_sha256 = None
        if staged_blob and statuses[relative][0] != "?":
            staged_sha256 = sha256_bytes(run_git(source, "cat-file", "blob", staged_blob))

        destination_path = destination / Path(relative)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied_hash = sha256_file(destination_path)
        if copied_hash != working_hash:
            raise RuntimeError(f"copy hash mismatch for {relative}: {working_hash} != {copied_hash}")

        entries.append(
            {
                "path": relative,
                "classification": classification(relative),
                "source_status": statuses[relative],
                "working_sha256": working_hash,
                "staged_blob_hash": staged_blob,
                "staged_sha256": staged_sha256,
                "working_differs_from_staged": bool(staged_sha256 and staged_sha256 != working_hash),
                "source_branch": run_git(source, "branch", "--show-current").decode().strip(),
            }
        )

    am_paths = sorted(entry["path"] for entry in entries if entry["source_status"] == "AM")
    return {
        "schema_version": "radle_v2_primary_preservation_manifest.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source.resolve()),
        "source_branch": run_git(source, "branch", "--show-current").decode().strip(),
        "source_head": run_git(source, "rev-parse", "HEAD").decode().strip(),
        "incremental_comparison_head": run_git(incremental, "rev-parse", "HEAD").decode().strip(),
        "primary_only_changed_path_count": len(primary_only),
        "selected_path_count": len(entries),
        "excluded_paths": sorted(EXCLUDED_PATHS & set(statuses)),
        "overlap_paths_preserved": sorted(set(selected) & incremental_paths),
        "am_paths": am_paths,
        "entries": entries,
    }


def verify_manifest(destination: Path, manifest_path: Path) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        path = destination / entry["path"]
        if not path.is_file():
            raise RuntimeError(f"preserved path missing: {entry['path']}")
        actual = sha256_file(path)
        if actual != entry["working_sha256"]:
            raise RuntimeError(f"preserved hash mismatch: {entry['path']} {actual}")
    if len(payload.get("am_paths", [])) != 5:
        raise RuntimeError(f"expected five AM paths, got {payload.get('am_paths')}")
    print(f"PRESERVATION_RESULT=PASS paths={len(payload['entries'])} am_paths=5")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--incremental", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.verify_only:
        verify_manifest(args.destination, args.manifest)
        return 0

    payload = build_manifest(args.source, args.destination, args.incremental)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify_manifest(args.destination, args.manifest)
    print(
        "PRESERVATION_INVENTORY="
        f"primary_only={payload['primary_only_changed_path_count']} selected={payload['selected_path_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
