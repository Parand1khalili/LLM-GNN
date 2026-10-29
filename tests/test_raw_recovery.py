"""Synthetic recovery-tool tests. These are NOT historical replay tests."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

from scripts import admission
from scripts import colab_recover_responses as recovery


def encoded(obj):
    return (json.dumps(obj, sort_keys=True) + "\n").encode()


class RecoveryFixture:
    def __init__(self, base):
        self.root = Path(base) / "Prnd-project" / "LLMGNN_reference"
        self.output = Path(base) / "exports"
        self.project = Path(base) / "local_project"
        self.records = []
        for node in range(140):
            kind = "historical_reuse" if node < 14 else "supplementary" if node < 19 else "original_fresh"
            prefix = {"historical_reuse": recovery.ALLOWED_RAW_PREFIXES[2],
                      "supplementary": recovery.ALLOWED_RAW_PREFIXES[1],
                      "original_fresh": recovery.ALLOWED_RAW_PREFIXES[0]}[kind]
            for arm in ("b1", "narrative_v0"):
                for sample in range(3):
                    index = len(self.records)
                    name = prefix + f"fixture_{index}/response.json"
                    blob = encoded({"synthetic_bytes_only": index})
                    path = self.root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(blob)
                    self.records.append({"target_id": node, "arm": arm, "sample_index": sample,
                                         "original_request_index": index, "source_kind": kind,
                                         "source_response_path": name, "source_response_sha256": recovery.sha256(blob)})
        self.node = {"selected_global_node_ids_sorted": list(range(140))}
        self.merged = {"records": self.records}
        node_blob, merged_blob = encoded(self.node), encoded(self.merged)
        self.pins = recovery.sha256(node_blob), recovery.sha256(merged_blob)
        for name, blob in ((recovery.NODE_MANIFEST, node_blob), (recovery.MERGED_MANIFEST, merged_blob)):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        (self.project / "manifests").mkdir(parents=True)
        source = self.project / "recovered_sources" / "never_execute.py"
        source.parent.mkdir()
        source.write_bytes(b'raise AssertionError("Historical source must never execute")\n')
        source_manifest = {"files": [{"local_path": "recovered_sources/never_execute.py",
                                     "sha256": recovery.sha256(source.read_bytes()), "size_bytes": source.stat().st_size}]}
        for name, obj in (("recovered_sources.json", source_manifest),
                          ("raw_response_requirements.json", {"files": self.records}),
                          ("unresolved_raw_responses.json", {"files": self.records[:48]})):
            (self.project / "manifests" / name).write_bytes(encoded(obj))

    def bundle(self, scope="all_selected"):
        return recovery.export_bundle(self.root, self.output, scope, self.pins)


def rewrite_zip(path, transform):
    with zipfile.ZipFile(path) as archive:
        contents = {i.filename: archive.read(i) for i in archive.infolist()}
    transform(contents)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, blob in contents.items():
            archive.writestr(name, blob)


class PathAndManifestTests(unittest.TestCase):
    def test_reject_path_traversal_and_windows_paths(self):
        for path in ("../file", "/file", "C:/file", "a\\b", "a//b", "a/./b", "a/../b", "a/", "a\x00b"):
            with self.subTest(path=path), self.assertRaises(recovery.RecoveryError):
                recovery.relative_path(path)

    def test_reject_duplicate_json_keys_and_nonfinite(self):
        for blob in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'not JSON'):
            with self.subTest(blob=blob), self.assertRaises(recovery.RecoveryError):
                recovery.strict_json(blob)

    def test_manifest_duplicate_path_conflict(self):
        with tempfile.TemporaryDirectory() as base:
            f = RecoveryFixture(base)
            f.records[1]["source_response_path"] = f.records[0]["source_response_path"]
            with self.assertRaisesRegex(recovery.RecoveryError, "DUPLICATE_PATH_CONFLICT"):
                recovery.validate_plan(f.node, f.merged)

    def test_missing_sample_and_boolean_node_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            f = RecoveryFixture(base)
            with self.assertRaises(recovery.RecoveryError):
                recovery.validate_plan(f.node, {"records": f.records[:-1]})
            f.node["selected_global_node_ids_sorted"][0] = False
            with self.assertRaises(recovery.RecoveryError):
                recovery.validate_plan(f.node, f.merged)

    def test_wrong_pinned_manifest_stops_before_export(self):
        with tempfile.TemporaryDirectory() as base:
            f = RecoveryFixture(base)
            (f.root / recovery.MERGED_MANIFEST).write_bytes(b'{}')
            with self.assertRaisesRegex(recovery.RecoveryError, "HASH_MISMATCH"):
                f.bundle()
            self.assertFalse(f.output.exists())

    def test_no_graph_or_other_path_can_be_in_manifest(self):
        with tempfile.TemporaryDirectory() as base:
            f = RecoveryFixture(base)
            f.records[0]["source_response_path"] = "LLMGNN_data/cora_random_sbert.pt"
            with self.assertRaisesRegex(recovery.RecoveryError, "DISALLOWED_RESPONSE_REFERENCE"):
                recovery.validate_plan(f.node, f.merged)


class BundleAndAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = RecoveryFixture(self.temp.name)

    def test_full_840_hash_admission_stops_before_replay(self):
        archive, report, digest = self.f.bundle()
        self.assertEqual(report["raw_hashes_verified"], 840)
        self.assertEqual(report["reused_hashes_verified"], 84)
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), digest)
        result = admission.verify(self.f.project, [archive], pins=self.f.pins)
        self.assertEqual(result["full_raw_admission"], "PASS")
        self.assertEqual(result["raw_hashes_verified_this_run"], 840)
        self.assertEqual(result["verified_by_source_kind"], {"historical_reuse":84,"supplementary":30,"original_fresh":726})
        self.assertEqual(result["next_action"], "STOP_FOR_USER_APPROVAL_BEFORE_REPLAY")
        self.assertEqual(result["parser_voter_replay"], "NOT_RUN")

    def test_reused_only_does_not_admit_unchecked_fresh(self):
        archive, report, _ = self.f.bundle("historical_reuse")
        self.assertEqual(report["raw_hashes_verified"], 84)
        result = admission.verify(self.f.project, [archive], pins=self.f.pins)
        self.assertEqual(result["full_raw_admission"], "BLOCKED")
        self.assertEqual(result["missing_raw_count"], 756)
        self.assertEqual(result["verified_by_source_kind"]["original_fresh"], 0)

    def test_missing_input_report_keeps_exact_expected_path_and_hash(self):
        row = self.f.records[0]
        (self.f.root / row["source_response_path"]).unlink()  # Synthetic test fixture only.
        archive, report, _ = self.f.bundle("historical_reuse")
        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["raw_hashes_verified"], 83)
        self.assertEqual(report["failures"][0]["path"], row["source_response_path"])
        self.assertEqual(report["failures"][0]["expected_sha256"], row["source_response_sha256"])
        self.assertEqual(report["failures"][0]["reason"], "MISSING_OR_INACCESSIBLE")
        self.assertEqual(admission.verify(self.f.project, [archive], pins=self.f.pins)["full_raw_admission"], "BLOCKED")

    def test_changed_raw_file_is_excluded_and_reported(self):
        row = self.f.records[0]
        (self.f.root / row["source_response_path"]).write_bytes(b'altered synthetic input')
        archive, report, _ = self.f.bundle("historical_reuse")
        self.assertEqual(report["failures"][0]["reason"], "HASH_MISMATCH")
        with zipfile.ZipFile(archive) as z:
            self.assertNotIn(row["source_response_path"], z.namelist())

    def test_zip_rejects_self_consistent_tampered_response(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        name = self.f.records[0]["source_response_path"]
        def tamper(contents):
            contents[name] = b'malicious substitute'
            hashes = json.loads(contents[recovery.SHA_MANIFEST])
            hashes["files"][name] = recovery.sha256(contents[name])
            contents[recovery.SHA_MANIFEST] = encoded(hashes)
        rewrite_zip(archive, tamper)
        with self.assertRaisesRegex(recovery.RecoveryError, "HISTORICAL_RAW_HASH_CONFLICT"):
            admission.verify(self.f.project, [archive], pins=self.f.pins)

    def test_zip_report_claims_are_not_trusted(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        def tamper(contents):
            report = json.loads(contents[recovery.REPORT_NAME]); report["all_840_raw_bytes_verified"] = True
            contents[recovery.REPORT_NAME] = encoded(report)
            hashes = json.loads(contents[recovery.SHA_MANIFEST]);hashes["files"][recovery.REPORT_NAME] = recovery.sha256(contents[recovery.REPORT_NAME])
            contents[recovery.SHA_MANIFEST] = encoded(hashes)
        rewrite_zip(archive, tamper)
        self.assertEqual(admission.verify(self.f.project, [archive], pins=self.f.pins)["full_raw_admission"], "BLOCKED")

    def test_zip_duplicate_path_rejected(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as z:
                z.writestr(recovery.REPORT_NAME, b'{}')
        with self.assertRaisesRegex(recovery.RecoveryError, "DUPLICATE_ZIP_MEMBER"):
            admission.verify(self.f.project, [archive], pins=self.f.pins)

    def test_zip_expected_member_symlink_rejected(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        with zipfile.ZipFile(archive) as z:
            contents = {i.filename: z.read(i) for i in z.infolist()}
        target = self.f.records[0]["source_response_path"]
        with zipfile.ZipFile(archive, "w") as z:
            for name, blob in contents.items():
                info = zipfile.ZipInfo(name)
                if name == target:
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, blob)
        with self.assertRaisesRegex(recovery.RecoveryError, "ZIP_SYMLINK_REJECTED"):
            admission.verify(self.f.project, [archive], pins=self.f.pins)

    def test_invalid_checksum_value_is_not_echoed(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        def tamper(contents):
            hashes = json.loads(contents[recovery.SHA_MANIFEST])
            hashes["files"][recovery.REPORT_NAME] = "DO_NOT_LOG_SYNTHETIC_SENSITIVE_BODY"
            contents[recovery.SHA_MANIFEST] = encoded(hashes)
        rewrite_zip(archive, tamper)
        with self.assertRaisesRegex(recovery.RecoveryError, "ZIP_HASH_MANIFEST_SCHEMA") as caught:
            admission.verify(self.f.project, [archive], pins=self.f.pins)
        self.assertNotIn("SENSITIVE_BODY", str(caught.exception.record()))

    def test_damaged_zip_fails_closed(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        archive.write_bytes(b'not a valid ZIP')
        with self.assertRaisesRegex(recovery.RecoveryError, "ZIP_INVALID_OR_UNREADABLE"):
            admission.verify(self.f.project, [archive], pins=self.f.pins)

    def test_raw_root_forbidden_graph_reference_rejected_before_read(self):
        manifest = self.f.project / 'manifests/raw_response_requirements.json'
        obj = json.loads(manifest.read_bytes())
        obj['files'][0]['source_response_path'] = 'LLMGNN_data/cora_random_sbert.pt'
        manifest.write_bytes(encoded(obj))
        with self.assertRaisesRegex(recovery.RecoveryError, "LOCAL_REFERENCE_MAPPING_INVALID"):
            admission.verify(self.f.project, raw_root=self.f.root, pins=self.f.pins)

    def test_zip_traversal_and_symlink_rejected(self):
        for kind in ("traversal", "symlink"):
            with self.subTest(kind=kind):
                archive, _, _ = self.f.bundle("historical_reuse")
                with zipfile.ZipFile(archive, "a") as z:
                    if kind == "traversal":
                        z.writestr("../escape", b'bad')
                    else:
                        info = zipfile.ZipInfo("experiments/matched_cora/extra.json")
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        z.writestr(info, b'/outside')
                with self.assertRaises(recovery.RecoveryError):
                    admission.verify(self.f.project, [archive], pins=self.f.pins)

    def test_real_filesystem_symlink_rejected(self):
        link = Path(self.temp.name) / "linked_root"
        try:
            link.symlink_to(self.f.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("OS account cannot create symbolic links; ZIP symlink rejection is tested separately")
        with self.assertRaisesRegex(recovery.RecoveryError, "SYMLINK_REJECTED"):
            recovery.load_plan(link, self.f.pins)

    def test_output_inside_historical_project_rejected(self):
        with self.assertRaisesRegex(recovery.RecoveryError, "OUTPUT_INSIDE_HISTORICAL_ARCHIVE"):
            recovery.export_bundle(self.f.root, self.f.root.parent / "new_backup", pins=self.f.pins)

    def test_local_raw_root_can_complete_reused_bundle(self):
        archive, _, _ = self.f.bundle("historical_reuse")
        result = admission.verify(self.f.project, [archive], self.f.root, self.f.pins)
        self.assertEqual(result["full_raw_admission"], "PASS")
        self.assertEqual(result["raw_hashes_verified_this_run"], 840)

    def test_no_inputs_never_passes(self):
        result = admission.verify(self.f.project)
        self.assertEqual(result["raw_hashes_verified_this_run"], 0)
        self.assertEqual(result["full_raw_admission"], "BLOCKED")

    def test_cli_blocked_report_references_existing_manifest(self):
        destination = self.f.project / 'reports' / 'intake.json'
        with mock.patch.object(admission, '__file__', str(self.f.project / 'scripts' / 'admission.py')), \
                mock.patch.object(sys, 'argv', ['verify_intake.py', '--report', str(destination)]), \
                contextlib.redirect_stdout(io.StringIO()):
            code = admission.main()
        saved = json.loads(destination.read_text())
        self.assertEqual(code, 2)
        self.assertEqual(saved['raw_hashes_verified_this_run'], 0)
        self.assertEqual(saved['missing_raw_files_manifest'], 'manifests/raw_response_requirements.json')
        self.assertNotIn('missing_raw_files', saved)

    def test_cli_pass_requires_stop_for_approval(self):
        archive, _, _ = self.f.bundle()
        with mock.patch.object(admission, '__file__', str(self.f.project / 'scripts' / 'admission.py')), \
                mock.patch.object(sys, 'argv', ['verify_intake.py', '--bundle', str(archive)]), \
                mock.patch.object(recovery, 'NODE_MANIFEST_SHA256', self.f.pins[0]), \
                mock.patch.object(recovery, 'MERGED_MANIFEST_SHA256', self.f.pins[1]), \
                contextlib.redirect_stdout(io.StringIO()) as console:
            code = admission.main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(console.getvalue())['next_action'], 'STOP_FOR_USER_APPROVAL_BEFORE_REPLAY')

    def test_recovered_source_conflict_stops_admission(self):
        (self.f.project / "recovered_sources/never_execute.py").write_bytes(b'changed')
        with self.assertRaisesRegex(recovery.RecoveryError, "HASH_MISMATCH"):
            admission.verify(self.f.project)

    def test_no_gt_network_historical_execution_or_source_mutation(self):
        # All contents here are synthetic. Never read a real graph or label artifact.
        sentinel = self.f.root / "never_read_ground_truth.pt"
        sentinel.write_bytes(b'synthetic forbidden graph marker')
        before = {p.relative_to(self.f.root).as_posix(): recovery.sha256(p.read_bytes())
                  for p in self.f.root.rglob('*.json')}
        original_open = recovery.os.open
        def guarded_open(path, flags, *args, **kwargs):
            self.assertNotEqual(Path(path).suffix, '.pt', "GT graph access attempted")
            self.assertEqual(flags & (recovery.os.O_WRONLY | recovery.os.O_RDWR), 0)
            return original_open(path, flags, *args, **kwargs)
        console = io.StringIO()
        with mock.patch.object(socket.socket, 'connect', side_effect=AssertionError('network attempted')), \
                mock.patch.object(recovery.os, 'open', side_effect=guarded_open), \
                contextlib.redirect_stdout(console):
            self.f.bundle()
        after = {p.relative_to(self.f.root).as_posix(): recovery.sha256(p.read_bytes())
                 for p in self.f.root.rglob('*.json')}
        self.assertEqual(before, after)
        self.assertEqual(console.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
