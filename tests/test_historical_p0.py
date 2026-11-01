"""P0 selection contracts, pinned admission and preservation of the separate pilot."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.io.frozen import InputError, load_frozen, read_pinned_json
from llmgnn_sara.pilot.historical_p0 import (GROUPS, MANIFEST_SHA256,
                                            _validate_selection, validate_p0)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/historical_p0.json"
FROZEN = ROOT / ".local_artifacts/frozen"


class ManifestTests(unittest.TestCase):
    def test_pinned_manifest_contract(self):
        manifest = read_pinned_json(MANIFEST, MANIFEST_SHA256)
        self.assertEqual(manifest["groups"], {g: list(ids) for g, ids in GROUPS.items()})
        self.assertEqual(len(manifest["logical_records"]), 12)
        self.assertEqual(set(manifest["missing_evidence"].values()), {"MISSING_EVIDENCE"})
        self.assertEqual(manifest["v1_generation_calls_per_record"], "UNKNOWN_DO_NOT_ASSUME_TWO")

    def test_tampered_hash_provenance_and_gt_rejected(self):
        original = json.loads(MANIFEST.read_bytes())
        for mutation in ({"status": "RECOVERED_EXACT"}, {"historical_sources": []},
                         {"frozen_input_sha256": {}}, {"y": [1]}):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as base:
                path = Path(base) / "manifest.json"
                path.write_text(json.dumps({**original, **mutation}), encoding="utf-8")
                with self.assertRaises(InputError): read_pinned_json(path, MANIFEST_SHA256)


@unittest.skipUnless(all((FROZEN / n).is_file() for n in
                        ("b1_final_predictions.json", "narrative_v0_final_predictions.json",
                         "selection_manifest.json")), "External pinned frozen inputs not provided")
class FrozenP0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read_pinned_json(MANIFEST, MANIFEST_SHA256)
        cls.dataset = load_frozen(FROZEN / "b1_final_predictions.json",
                                  FROZEN / "narrative_v0_final_predictions.json",
                                  FROZEN / "selection_manifest.json")

    def test_admitted_eight_nodes_twelve_records_and_hh_without_network(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            result = validate_p0(MANIFEST, FROZEN)
        self.assertEqual((result["unique_nodes"], result["logical_records"]), (8, 12))
        self.assertEqual(result["arm_counts"], {"Judge002": 4, "SARA3_V1": 8})
        self.assertEqual([r["node_id"] for r in result["group_b_checks"]], list(GROUPS["B"]))
        self.assertTrue(all(r["agreement"] and r["hh"] for r in result["group_b_checks"]))
        self.assertFalse(result["ground_truth_accessed"])
        self.assertEqual(result["historical_r1_membership"], "REPORTED_UNVERIFIED")

    def test_membership_order_uniqueness_and_arm_counts(self):
        for field in ("substitute", "duplicate", "wrong_arm", "missing", "extra", "reorder"):
            manifest = copy.deepcopy(self.manifest)
            records = manifest["logical_records"]
            if field == "substitute": manifest["groups"]["A"][0] = 637
            if field == "duplicate": records[1] = records[0].copy()
            if field == "wrong_arm": records[-1]["arm"] = "Judge002"
            if field == "missing": records.pop()
            if field == "extra": records.append(records[0].copy())
            if field == "reorder": records.reverse()
            with self.subTest(field=field), self.assertRaises(InputError):
                _validate_selection(manifest, self.dataset)

    def test_unverified_or_misaligned_dataset_rejected(self):
        datasets = (replace(self.dataset, artifact_hashes=(), input_evidence="UNVERIFIED"),
                    replace(self.dataset, artifact_hashes=(("b1", "0" * 64),)),
                    replace(self.dataset, target_ids=self.dataset.target_ids[1:]),
                    replace(self.dataset, predictions=self.dataset.predictions[1:]))
        for dataset in datasets:
            with self.subTest(dataset=dataset.input_evidence), self.assertRaises(InputError):
                _validate_selection(self.manifest, dataset)

    def test_group_b_disagreement_and_low_confidence_rejected(self):
        for field in ("agreement", "confidence"):
            rows = list(self.dataset.predictions)
            i = next(i for i, r in enumerate(rows) if r.target_id == 1031 and r.arm == "b1")
            row = rows[i]
            rows[i] = (replace(row, class_index=(row.class_index + 1) % 7,
                               prediction=self.dataset.classes[(row.class_index + 1) % 7])
                       if field == "agreement" else replace(row, confidence_percent=79.999))
            with self.subTest(field=field), self.assertRaises(InputError):
                _validate_selection(self.manifest, replace(self.dataset, predictions=tuple(rows)))

    def test_gt_fields_and_hh_claims_rejected(self):
        for field in ("y", "e0", "test_labels"):
            manifest = copy.deepcopy(self.manifest)
            manifest["logical_records"][0][field] = [0]
            with self.subTest(field=field), self.assertRaisesRegex(InputError, "GT/diagnostic"):
                _validate_selection(manifest, self.dataset)
        manifest = copy.deepcopy(self.manifest)
        manifest["group_b_contract"]["historical_r1_membership"] = "VERIFIED"
        with self.assertRaises(InputError): _validate_selection(manifest, self.dataset)

    def test_frozen_byte_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            for name in ("b1_final_predictions.json", "narrative_v0_final_predictions.json", "selection_manifest.json"):
                (root / name).write_bytes((FROZEN / name).read_bytes())
            with (root / "b1_final_predictions.json").open("ab") as stream: stream.write(b" ")
            with self.assertRaisesRegex(InputError, "SHA-256 mismatch"): validate_p0(MANIFEST, root)

    def test_existing_six_node_seal_preserved(self):
        root = ROOT / ".local_artifacts/pilot-gapapi"
        if not root.is_dir(): self.skipTest("Separate six-node seal not provided")
        before = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in root.rglob("*") if p.is_file()}
        self.assertEqual(before["SHA256.json"], "29fa95c7d34f5826b628509e6bad2baced83ac986ebfbc7cadc4bb36d4c31b41")
        self.assertEqual(before["pilot/SHA256.json"], "9fd65d82e3cab296afc503813b97b0c0af9e8f4dcb41cd0be1aa20ac34ef1f96")
        validate_p0(MANIFEST, FROZEN)
        after = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        for rel in ("SHA256.json", "pilot/SHA256.json"):
            seal = json.loads((root / rel).read_bytes())
            for name, digest in seal["files"].items():
                self.assertEqual(hashlib.sha256((root / rel).parent.joinpath(name).read_bytes()).hexdigest(), digest)
