"""Verify source evidence and replay admission without importing recovered code."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify(root: Path) -> dict:
    source_manifest = json.loads((root / "manifests/recovered_sources.json").read_text(encoding="utf-8"))
    requirements = json.loads((root / "manifests/raw_response_requirements.json").read_text(encoding="utf-8"))
    unresolved = json.loads((root / "manifests/unresolved_raw_responses.json").read_text(encoding="utf-8"))
    root = root.resolve()
    verified = 0
    for item in source_manifest["files"]:
        relative = Path(item["local_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe manifest path")
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Source path escapes workspace")
        blob = path.read_bytes()
        if len(blob) != item["size_bytes"] or hashlib.sha256(blob).hexdigest() != item["sha256"]:
            raise ValueError(f"Historical source hash conflict: {relative}")
        verified += 1
    records = requirements["files"]
    keys = {(r["target_id"], r["arm"], r["sample_index"]) for r in records}
    if len(records) != 840 or len(keys) != 840:
        raise ValueError("Unreconciled raw-response identity mapping")
    expected = {r["source_response_path"]: r["source_response_sha256"] for r in records}
    for item in unresolved["files"]:
        if expected.get(item["source_response_path"]) != item["source_response_sha256"]:
            raise ValueError("Unresolved-file manifest differs from full replay requirements")
    # Neither folder discovery nor zero unresolved entries would prove readback.
    # Full raw admission is deliberately not inferred by this intake-only tool.
    return {
        "source_integrity": "PASS",
        "verified_source_count": verified,
        "raw_reference_mapping": "PASS",
        "required_raw_count": len(records),
        "unresolved_raw_folder_count": len(unresolved["files"]),
        "full_raw_admission": "BLOCKED",
        "parser_voter_replay": "NOT_RUN",
        "runtime_GT_isolation_tests": "NOT_RUN",
        "recovered_code_executed": False,
        "GT_decoded": False,
        "provider_calls": 0,
        "training_runs": 0,
    }


def main() -> int:
    result = verify(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
