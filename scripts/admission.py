"""Offline byte admission. No extraction, provider, GT, historical imports or replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat
import zipfile
import zlib

try:
    from . import colab_recover_responses as recovery
except ImportError:
    import colab_recover_responses as recovery

RecoveryError = recovery.RecoveryError


def check_bundle(path: Path, expected: dict[str, str], pins=None) -> dict[str, str]:
    """Read ZIP members in place; recompute coverage instead of trusting its report."""
    recovery.no_symlink_chain(path)
    metadata = {recovery.NODE_MANIFEST, recovery.MERGED_MANIFEST,
                recovery.REPORT_NAME, recovery.SHA_MANIFEST}
    try:
        if not path.is_file() or path.stat().st_size > recovery.MAX_BUNDLE_BYTES:
            raise RecoveryError("ZIP_FILE_SIZE_LIMIT")
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                raise RecoveryError("DUPLICATE_ZIP_MEMBER")
            if len(names) > len(expected) + len(metadata):
                raise RecoveryError("ZIP_ENTRY_LIMIT")
            if sum(i.file_size for i in infos) > recovery.MAX_BUNDLE_BYTES:
                raise RecoveryError("ZIP_EXPANSION_LIMIT")
            for info in infos:
                recovery.relative_path(info.filename)
                if info.filename not in set(expected) | metadata or info.is_dir():
                    raise RecoveryError("UNEXPECTED_ZIP_MEMBER", info.filename)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise RecoveryError("ZIP_SYMLINK_REJECTED", info.filename)
                if info.flag_bits & 1 or info.file_size > recovery.MAX_FILE_BYTES:
                    raise RecoveryError("ZIP_ENCRYPTED_OR_OVERSIZED_MEMBER", info.filename)
            if not metadata.issubset(names):
                raise RecoveryError("ZIP_METADATA_MISSING")
            if archive.testzip() is not None:
                raise RecoveryError("ZIP_CRC_FAILURE")
            checksums = recovery.strict_json(archive.read(recovery.SHA_MANIFEST))
            hashes = checksums.get("files") if isinstance(checksums, dict) else None
            if not isinstance(hashes, dict) or set(hashes) != set(names) - {recovery.SHA_MANIFEST}:
                raise RecoveryError("ZIP_HASH_MANIFEST_COVERAGE")
            if any(not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin) for pin in hashes.values()):
                raise RecoveryError("ZIP_HASH_MANIFEST_SCHEMA")
            actual = {}
            for name, pin in hashes.items():
                digest = recovery.sha256(archive.read(name))
                if digest != pin:
                    raise RecoveryError("ZIP_MEMBER_HASH_MISMATCH", name, str(pin), digest)
                actual[name] = digest
            node_pin, merged_pin = pins or (recovery.NODE_MANIFEST_SHA256, recovery.MERGED_MANIFEST_SHA256)
            if (actual[recovery.NODE_MANIFEST] != node_pin
                    or actual[recovery.MERGED_MANIFEST] != merged_pin):
                raise RecoveryError("HISTORICAL_MANIFEST_HASH_CONFLICT")
            records = recovery.validate_plan(
                recovery.strict_json(archive.read(recovery.NODE_MANIFEST)),
                recovery.strict_json(archive.read(recovery.MERGED_MANIFEST)))
            original = {r["source_response_path"]: r["source_response_sha256"] for r in records}
            if original != expected:
                raise RecoveryError("LOCAL_AND_ORIGINAL_REFERENCE_MAPPING_DIFFER")
            for name in set(actual) & set(expected):
                if actual[name] != expected[name]:
                    raise RecoveryError("HISTORICAL_RAW_HASH_CONFLICT", name, expected[name], actual[name])
            return {name: actual[name] for name in actual if name in expected}
    except RecoveryError:
        raise
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, KeyError, EOFError, zlib.error):
        raise RecoveryError("ZIP_INVALID_OR_UNREADABLE") from None


def verify(root: Path, bundles=(), raw_root: Path | None = None, pins=None) -> dict:
    root = root.resolve(strict=True)
    source_manifest = recovery.strict_json((root / "manifests/recovered_sources.json").read_bytes())
    requirements = recovery.strict_json((root / "manifests/raw_response_requirements.json").read_bytes())
    unresolved = recovery.strict_json((root / "manifests/unresolved_raw_responses.json").read_bytes())
    for item in source_manifest["files"]:
        blob = recovery.read_original(root, item["local_path"], item["sha256"])
        if len(blob) != item["size_bytes"]:
            raise RecoveryError("SOURCE_SIZE_CONFLICT", item["local_path"])
    records = requirements["files"]
    identities = {(r["target_id"], r["arm"], r["sample_index"]) for r in records}
    expected = {r["source_response_path"]: r["source_response_sha256"] for r in records}
    kinds = {}
    for record in records:
        path, pin = record["source_response_path"], record["source_response_sha256"]
        recovery.relative_path(path)
        if (not path.startswith(recovery.ALLOWED_RAW_PREFIXES) or not path.endswith(".json")
                or not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin)
                or type(record["target_id"]) is not int or not 0 <= record["target_id"] < 2708
                or record["arm"] not in ("b1", "narrative_v0")
                or type(record["sample_index"]) is not int or record["sample_index"] not in (0, 1, 2)):
            raise RecoveryError("LOCAL_REFERENCE_MAPPING_INVALID")
        kind = record["source_kind"]
        kinds[kind] = kinds.get(kind, 0) + 1
    if (len(records) != 840 or len(identities) != 840 or len(expected) != 840
            or kinds != {"original_fresh": 726, "supplementary": 30, "historical_reuse": 84}):
        raise RecoveryError("LOCAL_REFERENCE_MAPPING_INVALID")
    for item in unresolved["files"]:
        if expected.get(item["source_response_path"]) != item["source_response_sha256"]:
            raise RecoveryError("UNRESOLVED_MANIFEST_CONFLICT")
    verified, bundle_checks = {}, []
    for bundle in bundles:
        discovered = check_bundle(Path(bundle), expected, pins)
        verified.update(discovered)  # Every entry was compared with the same immutable expected hash.
        bundle_checks.append({"zip_sha256": recovery.sha256(Path(bundle).read_bytes()),
                              "raw_hashes_verified": len(discovered), "status": "PASS"})
    missing = []
    for record in records:
        name, pin = record["source_response_path"], record["source_response_sha256"]
        if name in verified:
            continue
        if raw_root is not None:
            try:
                recovery.read_original(raw_root, name, pin)
                verified[name] = pin
                continue
            except RecoveryError as error:
                if error.reason != "MISSING_OR_INACCESSIBLE":
                    raise
        missing.append({"path": name, "expected_sha256": pin,
                        "reason": "RAW_BYTES_NOT_PROVIDED_OR_UNREADABLE"})
    if raw_root is not None and not bundles:
        original, _ = recovery.load_plan(raw_root, pins)
        if {r["source_response_path"]: r["source_response_sha256"] for r in original} != expected:
            raise RecoveryError("LOCAL_AND_ORIGINAL_REFERENCE_MAPPING_DIFFER")
    counts = {kind: sum(r["source_kind"] == kind and r["source_response_path"] in verified for r in records)
              for kind in kinds}
    admitted = len(verified) == 840 and not missing and bool(bundles or raw_root)
    return {"source_integrity": "PASS", "verified_source_count": len(source_manifest["files"]),
            "raw_reference_mapping": "PASS", "required_raw_count": 840,
            "raw_hashes_verified_this_run": len(verified), "verified_by_source_kind": counts,
            "historical_unresolved_folder_count": len(unresolved["files"]),
            "missing_raw_count": len(missing), "missing_raw_files": missing,
            "bundle_checks": bundle_checks, "full_raw_admission": "PASS" if admitted else "BLOCKED",
            "parser_voter_replay": "NOT_RUN", "runtime_GT_isolation_tests": "NOT_RUN",
            "recovered_code_executed": False, "GT_decoded": False, "provider_calls": 0, "training_runs": 0,
            "next_action": "STOP_FOR_USER_APPROVAL_BEFORE_REPLAY" if admitted else "RECOVER_AND_VERIFY_REMAINING_RAW_BYTES"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, action="append", default=[])
    parser.add_argument("--raw-root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    try:
        result = verify(project, args.bundle, args.raw_root)
        code = 0 if result["full_raw_admission"] == "PASS" else 2
    except RecoveryError as error:
        result = {"full_raw_admission": "FAIL", **error.record(),
                  "parser_voter_replay": "NOT_RUN", "next_action": "STOP_AND_REPORT"}
        code = 1
    if args.report:
        recovery.no_symlink_chain(args.report)
        destination = args.report.resolve()
        if not destination.is_relative_to(project / "reports"):
            raise SystemExit("Report destination must be inside this project's reports directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        saved = dict(result)
        if not args.bundle and args.raw_root is None and "missing_raw_files" in saved:
            saved.pop("missing_raw_files")
            saved["missing_raw_files_manifest"] = "manifests/raw_response_requirements.json"
            saved["missing_raw_reason"] = "NO_RAW_INPUT_BYTES_PROVIDED_THIS_RUN"
        destination.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "missing_raw_files"}, indent=2))
    return code
