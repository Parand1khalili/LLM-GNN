"""Paste this entire file into ONE Colab code cell using the archive owner's account.

Only Drive mounting and browser download are interactive. All recovery work uses
the standard library and reads pinned manifests and original response bytes.
No historical Python code is imported. No .pt file, GT or provider is accessed.
Default scope: all 840 selected responses, including all 84 historical reuses.
Set RECOVERY_SCOPE = 'historical_reuse' for an 84-only bundle; it cannot alone
establish complete 840-response admission.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

RECOVERY_SCOPE = "all_selected"
SOURCE_ROOT_OVERRIDE = ""  # Optional exact mounted LLMGNN_reference directory.
DRIVE_MOUNT = "/content/drive"
OUTPUT_BASE = "/content/sara_recovery_exports"  # Local runtime; never the archive.

NODE_MANIFEST = "experiments/matched_cora/featprop_selection_001/selection_manifest.json"
NODE_MANIFEST_SHA256 = "dc8260974c7c0ca2e828f2d069e2896e9bcf2c363b15ca81d9f09d2803c9b12c"
MERGED_MANIFEST = "experiments/matched_cora/featprop_merged_selection_001/selection_manifest.json"
MERGED_MANIFEST_SHA256 = "aea6ec0d0bc2f96d7fa706ac0456476631a2fded19abf461550729202ed18ee0"
SHA_MANIFEST = "RECOVERY_SHA256.json"
REPORT_NAME = "RECOVERY_REPORT.json"
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
ALLOWED_RAW_PREFIXES = (
    "experiments/matched_cora/featprop_infer_001/slots/",
    "experiments/matched_cora/featprop_reannotation_001/slots/",
    "experiments/matched_cora/matched_infer_003/requests/",
)


class RecoveryError(ValueError):
    """Safe structured error: never includes source file contents."""

    def __init__(self, reason: str, path: str = "", expected: str = "", actual: str = ""):
        self.reason, self.path, self.expected, self.actual = reason, path, expected, actual
        super().__init__(reason)

    def record(self) -> dict:
        return {"reason": self.reason, "path": self.path,
                "expected_sha256": self.expected, "actual_sha256": self.actual}


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def strict_json(blob: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RecoveryError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def invalid_constant(_):
        raise RecoveryError("NONFINITE_JSON_NUMBER")

    try:
        return json.loads(blob.decode("utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=invalid_constant)
    except RecoveryError:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise RecoveryError("INVALID_JSON") from None


def relative_path(value: str) -> PurePosixPath:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(ord(c) < 32 for c in value)):
        raise RecoveryError("UNSAFE_RELATIVE_PATH")
    parts = value.split("/")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in parts) or path.as_posix() != value:
        raise RecoveryError("UNSAFE_RELATIVE_PATH", value)
    return path


def no_symlink_chain(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            raise RecoveryError("SYMLINK_REJECTED")


def read_original(root: Path, relative: str, expected: str | None = None) -> bytes:
    rel = relative_path(relative)
    no_symlink_chain(root)
    try:
        canonical_root = root.resolve(strict=True)
        path = root.joinpath(*rel.parts)
        no_symlink_chain(path)
        if not path.resolve(strict=True).is_relative_to(canonical_root):
            raise RecoveryError("PATH_ESCAPE", relative)
        if not stat.S_ISREG(path.stat().st_mode):
            raise RecoveryError("NOT_REGULAR_FILE", relative)
        flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0))
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise RecoveryError("NOT_REGULAR_FILE", relative)
            if metadata.st_size > MAX_FILE_BYTES:
                raise RecoveryError("FILE_SIZE_LIMIT", relative)
            blob = stream.read(MAX_FILE_BYTES + 1)
        if len(blob) > MAX_FILE_BYTES:
            raise RecoveryError("FILE_SIZE_LIMIT", relative)
        no_symlink_chain(path)
        if not path.resolve(strict=True).is_relative_to(canonical_root):
            raise RecoveryError("PATH_ESCAPE", relative)
    except RecoveryError as error:
        raise RecoveryError(error.reason, relative, expected or "", error.actual) from None
    except OSError:
        raise RecoveryError("MISSING_OR_INACCESSIBLE", relative, expected or "") from None
    actual = sha256(blob)
    if expected is not None and actual != expected:
        raise RecoveryError("HASH_MISMATCH", relative, expected, actual)
    return blob


def validate_plan(node: dict, merged: dict) -> list[dict]:
    try:
        ids = node["selected_global_node_ids_sorted"]
        records = merged["records"]
        if (len(ids) != 140 or len(set(ids)) != 140 or ids != sorted(ids)
                or any(type(i) is not int or not 0 <= i < 2708 for i in ids)):
            raise RecoveryError("INVALID_NODE_SELECTION")
        if not isinstance(records, list) or len(records) != 840:
            raise RecoveryError("INVALID_RECORD_COUNT")
        identities, indices, paths, kinds = set(), set(), {}, {}
        for record in records:
            target, arm, sample = record["target_id"], record["arm"], record["sample_index"]
            index, kind = record["original_request_index"], record["source_kind"]
            if (type(target) is not int or target not in ids or arm not in ("b1", "narrative_v0")
                    or type(sample) is not int or sample not in (0, 1, 2)
                    or type(index) is not int or not 0 <= index < 840):
                raise RecoveryError("INVALID_RECORD_IDENTITY")
            identity = (target, arm, sample)
            if identity in identities or index in indices:
                raise RecoveryError("DUPLICATE_RECORD_IDENTITY")
            identities.add(identity)
            indices.add(index)
            path, pin = record["source_response_path"], record["source_response_sha256"]
            relative_path(path)
            if (not path.startswith(ALLOWED_RAW_PREFIXES) or not path.endswith(".json")
                    or not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin)):
                raise RecoveryError("DISALLOWED_RESPONSE_REFERENCE", path)
            if path in paths:
                reason = "DUPLICATE_PATH_CONFLICT" if paths[path] != pin else "DUPLICATE_RESPONSE_PATH"
                raise RecoveryError(reason, path)
            paths[path] = pin
            kinds[kind] = kinds.get(kind, 0) + 1
        if kinds != {"original_fresh": 726, "supplementary": 30, "historical_reuse": 84}:
            raise RecoveryError("SOURCE_KIND_COUNTS_DIFFER")
        if indices != set(range(840)):
            raise RecoveryError("REQUEST_ORDER_INCOMPLETE")
        return sorted(records, key=lambda r: r["original_request_index"])
    except RecoveryError:
        raise
    except (KeyError, TypeError, ValueError):
        raise RecoveryError("INVALID_MANIFEST_SCHEMA") from None


def load_plan(root: Path, pins: tuple[str, str] | None = None):
    node_pin, merged_pin = pins or (NODE_MANIFEST_SHA256, MERGED_MANIFEST_SHA256)
    node_blob = read_original(root, NODE_MANIFEST, node_pin)
    merged_blob = read_original(root, MERGED_MANIFEST, merged_pin)
    records = validate_plan(strict_json(node_blob), strict_json(merged_blob))
    return records, {NODE_MANIFEST: node_blob, MERGED_MANIFEST: merged_blob}


def locate_root(mount: Path, override: str = "") -> Path:
    mount = mount.resolve(strict=True)
    if override:
        candidate = Path(override)
        no_symlink_chain(candidate)
        if not candidate.resolve(strict=True).is_relative_to(mount):
            raise RecoveryError("ROOT_OUTSIDE_MOUNT")
        load_plan(candidate)
        return candidate
    mydrive = mount / "MyDrive"
    candidate = mydrive / "Prnd-project" / "LLMGNN_reference"
    if candidate.is_dir():
        load_plan(candidate)  # Existing manifests and pins, not the name, establish identity.
        return candidate
    candidates, visited = [], 0
    for directory, children, _ in os.walk(mydrive, followlinks=False):
        visited += 1
        current = Path(directory)
        depth = len(current.relative_to(mydrive).parts)
        children[:] = [name for name in children if not (current / name).is_symlink()
                       and name not in {".git", "__pycache__", "LLMGNN_data", "env_backup", "api_runs"}]
        if depth >= 4:
            children[:] = []
        if visited > 5000:
            raise RecoveryError("ROOT_SEARCH_LIMIT_SET_OVERRIDE")
        if current.name == "LLMGNN_reference":
            load_plan(current)
            candidates.append(current)
            children[:] = []
    if len(candidates) != 1:
        raise RecoveryError("ROOT_NOT_UNIQUE_SET_OVERRIDE")
    return candidates[0]


def export_bundle(root: Path, output_base: Path, scope: str = "all_selected",
                  pins: tuple[str, str] | None = None, forbidden_output_root: Path | None = None):
    if scope not in ("all_selected", "historical_reuse"):
        raise RecoveryError("INVALID_SCOPE")
    records, context = load_plan(root, pins)
    selected = records if scope == "all_selected" else [r for r in records if r["source_kind"] == scope]
    no_symlink_chain(output_base)
    resolved_output = output_base.resolve()
    historical_project = root.resolve().parent
    if resolved_output.is_relative_to(historical_project):
        raise RecoveryError("OUTPUT_INSIDE_HISTORICAL_ARCHIVE")
    if forbidden_output_root and resolved_output.is_relative_to(forbidden_output_root.resolve()):
        raise RecoveryError("OUTPUT_INSIDE_DRIVE_MOUNT")
    output_base.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="sara-raw-recovery-", dir=output_base))
    archive_path = destination / "SARA_RAW_RESPONSES.zip"
    verified, failures, hashes, total = [], [], {}, sum(map(len, context.values()))
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, blob in context.items():
            archive.writestr(name, blob)
            hashes[name] = sha256(blob)
        for record in selected:
            path, pin = record["source_response_path"], record["source_response_sha256"]
            try:
                blob = read_original(root, path, pin)
                if total + len(blob) > MAX_BUNDLE_BYTES:
                    raise RecoveryError("BUNDLE_SIZE_LIMIT", path, pin)
                archive.writestr(path, blob)  # Exact bytes already hashed; never re-read for packaging.
                hashes[path] = pin
                total += len(blob)
                verified.append({"path": path, "sha256": pin, "source_kind": record["source_kind"]})
            except RecoveryError as error:
                failures.append(error.record())
        reused_verified = sum(x["source_kind"] == "historical_reuse" for x in verified)
        report = {"schema": "sara.raw_recovery_report.v1", "scope": scope,
                  "status": "PASS" if not failures else "PARTIAL",
                  "source_root": str(root.resolve()), "required_in_scope": len(selected),
                  "raw_hashes_verified": len(verified), "reused_required": 84,
                  "reused_hashes_verified": reused_verified, "failures": failures,
                  "all_840_raw_bytes_verified": len(verified) == 840 and not failures,
                  "original_files_modified": False, "GT_decoded": False,
                  "provider_calls": 0, "training_runs": 0,
                  "next_action": "Return ZIP for independent local admission; do not implement or run replay."}
        report_blob = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        archive.writestr(REPORT_NAME, report_blob)
        hashes[REPORT_NAME] = sha256(report_blob)
        archive.writestr(SHA_MANIFEST, json.dumps({"schema": "sara.zip_hashes.v1", "files": hashes}, indent=2) + "\n")
    # Readback of ZIP structure/CRC is local; no archived Python code is executed.
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise RecoveryError("ZIP_CRC_FAILURE")
    report_path = destination / REPORT_NAME
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = sha256(archive_path.read_bytes())
    (destination / "ZIP_SHA256.txt").write_text(f"{digest}  {archive_path.name}\n", encoding="ascii")
    return archive_path, report, digest


def main() -> None:
    # Official interactive Colab mechanism; not imported during local testing.
    from google.colab import drive, files

    try:
        drive.mount(DRIVE_MOUNT)
        root = locate_root(Path(DRIVE_MOUNT), SOURCE_ROOT_OVERRIDE)
        archive, report, digest = export_bundle(
            root, Path(OUTPUT_BASE), RECOVERY_SCOPE, forbidden_output_root=Path(DRIVE_MOUNT))
        print(json.dumps({"status": report["status"], "scope": report["scope"],
                          "raw_hashes_verified": report["raw_hashes_verified"],
                          "reused_hashes_verified": report["reused_hashes_verified"],
                          "failure_count": len(report["failures"]), "zip_path": str(archive),
                          "zip_sha256": digest}, ensure_ascii=False, indent=2))
        if report["failures"]:
            print("PARTIAL: exact expected paths, hashes and reasons are in RECOVERY_REPORT.json inside the ZIP.")
        files.download(str(archive))
    except RecoveryError as error:
        print(json.dumps({"status": "FAIL", **error.record()}, ensure_ascii=False, indent=2))
        print("STOP. Do not substitute files, regenerate annotations or run historical code.")
    except Exception as error:
        # Exception text can contain provider/account data; log only its type.
        print(json.dumps({"status": "FAIL", "reason": "RECOVERY_ABORTED", "error_type": type(error).__name__}))


if __name__ == "__main__":
    main()
