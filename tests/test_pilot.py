"""Authentic integration, blind evidence, immutable seals and no live execution."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.io.frozen import InputError, read_pinned_json
from llmgnn_sara.io.project import PINS, load_project_inputs, _validate_project
from llmgnn_sara.annotation.prompts import FrozenPromptTemplate
from llmgnn_sara.sara2 import Annotation
from llmgnn_sara.sara3.inputs import canonical_bytes, pair_inputs, verifier_input
from llmgnn_sara.sara3.pipeline import LexicalFixtureVerifier, run_offline, validate_result
from llmgnn_sara.pilot import (DurablePilotLedger, PilotConfig, materialize_comparison,
                                seal_pilot, select_pilot, verify_pilot)
from llmgnn_sara.pilot.workflow import gapapi_body, historical_compatibility, prepare_authentic

ROOT = Path(__file__).resolve().parents[1]
FROZEN, AUTHENTIC = ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic"


class LedgerTests(unittest.TestCase):
    def test_persistent_cap_duplicates_uncertainty_and_seal_binding(self):
        with tempfile.TemporaryDirectory() as base:
            path = Path(base) / "ledger with spaces.sqlite"
            ledger = DurablePilotLedger(path, "a" * 64)
            ledger.begin("first", {"node_id": 1})
            ledger.settle("first", "UNCERTAIN")
            reopened = DurablePilotLedger(path, "a" * 64)
            with self.assertRaises(ValueError): reopened.begin("first", {"node_id": 1})
            with self.assertRaises(ValueError): reopened.begin("duplicate_body", {"node_id": 1})
            with self.assertRaises(ValueError): reopened.settle("first", "COMPLETED")
            with self.assertRaises(ValueError): DurablePilotLedger(path, "b" * 64)
            for i in range(2, 13): reopened.begin(str(i), {"node_id": i})
            with self.assertRaises(ValueError): reopened.begin("over_budget", {"node_id": 99})
            self.assertEqual(len(reopened.snapshot()), 12)
            self.assertEqual(reopened.snapshot()[0]["state"], "UNCERTAIN")

    def test_sensitive_fields_and_invalid_budget_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            ledger = DurablePilotLedger(Path(base) / "ledger.sqlite", "a" * 64)
            for payload in ({"y": 1}, {"authorization": "private sentinel"}):
                with self.assertRaises(ValueError): ledger.begin("bad", payload)
            self.assertEqual(ledger.snapshot(), [])
        for values in ({"max_generation_calls": 13}, {"per_router": 4}, {"retries": 1}):
            with self.assertRaises(ValueError): PilotConfig(**values)


@unittest.skipUnless(all((AUTHENTIC / n).is_file() for n in PINS)
                     and (FROZEN / "b1_final_predictions.json").is_file(),
                     "External pinned authentic inputs not provided")
class AuthenticPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_project_inputs(FROZEN, AUTHENTIC)

    def payloads(self, pairs=None):
        pairs = self.inputs.pairs if pairs is None else pairs
        wires = {p.node_id: pair_inputs(p) for p in pairs}
        return {n: w[0] for n, w in wires.items()}, {n: w[1] for n, w in wires.items()}

    def test_140_real_texts_graph_evidence_and_class_alignment(self):
        inputs = self.inputs
        self.assertEqual(len(inputs.pairs), 140)
        self.assertEqual(tuple(p.node_id for p in inputs.pairs), inputs.frozen.target_ids)
        self.assertTrue(all(p.text.strip() and p.neighborhood.neighbor_ids for p in inputs.pairs))
        self.assertTrue(all(p.neighborhood.target_id == p.node_id for p in inputs.pairs))
        self.assertTrue(all(p.neighborhood.verification_level.endswith("NOT_RECOMPUTED") for p in inputs.pairs))
        self.assertEqual(len(inputs.frozen.classes), 7)

    def test_counterfactual_votes_do_not_change_blind_bytes_or_atlas(self):
        pair = self.inputs.pairs[0]
        altered = replace(pair, b1=Annotation(pair.node_id, (pair.b1.class_index+1) % 7, 1),
                          narrative_v0=Annotation(pair.node_id, (pair.narrative_v0.class_index+2) % 7, 2))
        blind, comparison = pair_inputs(pair)
        changed, changed_comparison = pair_inputs(altered)
        self.assertEqual(canonical_bytes(blind), canonical_bytes(changed))
        self.assertNotEqual(comparison["historical_candidates"], changed_comparison["historical_candidates"])
        self.assertNotIn("historical_candidates", blind)
        self.assertIn("neighborhood", blind)
        self.assertIn("class_atlas", blind)
        self.assertIn("untrusted evidence", blind["instructions"])
        self.assertEqual(json.loads(gapapi_body(blind)["messages"][0]["content"]), blind)

    def test_gt_keys_and_changed_source_identity_fail_before_decoding(self):
        objects = {name: read_pinned_json(AUTHENTIC / name, pin) for name, pin in PINS.items()}
        template = FrozenPromptTemplate.from_receipt(FROZEN / "preparation_receipt.json")
        class Poison:
            def __int__(self): raise AssertionError("GT decoded")
        with self.assertRaises(ValueError): verifier_input(0, "Public paper text", Poison())
        bad, _ = pair_inputs(self.inputs.pairs[0])
        bad["y"] = 1
        with self.assertRaises(ValueError): gapapi_body(bad)
        changed = copy.deepcopy(objects)
        changed["neighborhoods.json"]["y"] = Poison()
        with self.assertRaises(InputError): _validate_project(self.inputs.frozen, template, changed)
        changed = copy.deepcopy(objects)
        changed["neighborhoods.json"]["target_ids_in_manifest_order"][0] = -1
        with self.assertRaises(InputError): _validate_project(self.inputs.frozen, template, changed)
        with tempfile.TemporaryDirectory() as base:
            path = Path(base) / "paper.json"
            path.write_text('{"y":123}', encoding="utf-8")
            with self.assertRaises(InputError): read_pinned_json(path, PINS["b1_prompts.json"])

    def test_neighbor_only_and_whitespace_quotes_cannot_support_target(self):
        text = "A legitimate target.\n "
        for quote in (" ", "\n", "different neighbor text"):
            with self.assertRaises(ValueError):
                validate_result({"class_index": 0, "abstain": False, "evidence": [quote]}, text)
        for reply in ({"class_index": True, "abstain": False, "evidence": [text]},
                      {"class_index": 7, "abstain": False, "evidence": [text]},
                      {"class_index": 0, "abstain": True, "evidence": []},
                      {"class_index": 0, "abstain": False, "evidence": [text], "confidence": 1}):
            with self.assertRaises(ValueError): validate_result(reply, text)

    def test_six_node_seal_readback_conditional_binding_and_immutability(self):
        blind, compare = self.payloads()
        with tempfile.TemporaryDirectory() as base:
            output = Path(base) / "sealed pilot with spaces"
            report = seal_pilot(self.inputs.pairs, blind, compare, output,
                                model="gpt-6-luna", provider="GapAPI")
            self.assertEqual(len(report["selection"]["selected_node_ids"]), 6)
            self.assertEqual(report["generation_call_cap"], 12)
            self.assertEqual(verify_pilot(output, report["manifest_sha256"])["verified_files"], 13)
            self.assertEqual(report["comparison_future_exact_bytes"], "CONDITIONAL_NOT_YET_KNOWN")
            self.assertIsNone(report["estimated_max_cost_usd_under_assumptions"])
            with self.assertRaises(FileExistsError): seal_pilot(self.inputs.pairs, blind, compare, output)
            node = report["selection"]["selected_node_ids"][0]
            for label in range(7):
                materialized = materialize_comparison(compare[node], label)
                self.assertEqual(materialized["blind_class_index"], label)
                self.assertEqual(materialized["neighborhood"], compare[node]["neighborhood"])
            with self.assertRaises(ValueError): materialize_comparison(compare[node], True)
            member = output / f"requests/blind-{node}.json"
            member.write_bytes(member.read_bytes() + b' ')
            with self.assertRaises(ValueError): verify_pilot(output, report["manifest_sha256"])

    def test_blind_prior_fields_bad_graph_hash_and_token_overflow_rejected(self):
        blind, compare = self.payloads()
        node = select_pilot(self.inputs.pairs)["selected_node_ids"][0]
        for change in ("prior", "target_hash", "graph"):
            bad = copy.deepcopy(blind)
            if change == "prior": bad[node]["target"]["votes"] = [0]
            elif change == "target_hash": bad[node]["target"]["source_sha256"] = "a"*64
            else: bad[node]["neighborhood"]["connected_pairs"] = []
            with tempfile.TemporaryDirectory() as base:
                output = Path(base) / "reject"
                with self.assertRaises(ValueError): seal_pilot(self.inputs.pairs, bad, compare, output)
                self.assertFalse(output.exists())
        with tempfile.TemporaryDirectory() as base:
            with self.assertRaises(ValueError):
                seal_pilot(self.inputs.pairs, blind, compare, Path(base)/"overflow", token_counter=lambda _: 20000)

    def test_deterministic_140_dry_run_has_exact_inputs_and_no_network(self):
        for router in ("r0", "semantic"):
            with patch.object(socket.socket, "connect", side_effect=AssertionError("Network attempted")):
                result = run_offline(self.inputs.pairs, 37, router, LexicalFixtureVerifier())
                repeated = run_offline(self.inputs.pairs, 37, router, LexicalFixtureVerifier())
            self.assertEqual(result, repeated)
            self.assertEqual(result["target_count"], 140)
            self.assertEqual(result["review_count"], 37)
            self.assertEqual(result["accepted_count"]+result["abstention_count"], 140)
            for item in result["verifier_inputs"]:
                self.assertEqual(item["sha256"], hashlib.sha256(canonical_bytes(item["payload"])).hexdigest())
                if item["payload"]["phase"] == "blind":
                    self.assertNotIn("historical_candidates", item["payload"])
            self.assertTrue(all(d["training_class_index"] is None for d in result["decisions"]
                                if d["third_class_proposal"] is not None))

    def test_full_workflow_actual_artifacts_and_abstentions_in_masks(self):
        with tempfile.TemporaryDirectory() as base, \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network attempted")):
            output = Path(base) / "authentic run"
            summary = prepare_authentic(FROZEN, AUTHENTIC, output)
            self.assertEqual(summary["targets"], 140)
            self.assertEqual(summary["provider_calls"], 0)
            plans = json.loads((output/"gcn_plans.json").read_bytes())
            for key, row in plans.items():
                plan = row["fixture_sara_not_measured"]
                self.assertEqual(plan["test_ids"], row["baselines"]["b1"]["test_ids"])
                self.assertTrue(all(plan["pseudo_y"][i] == -1 for i in plan["abstained_ids"]+plan["excluded_ids"]))
                self.assertTrue(set(plan["abstained_ids"]).isdisjoint(plan["test_ids"]))
                self.assertEqual(row["comparison_role"], "PRIMARY" if key.endswith('_ce') else "SUPPLEMENTARY_PREVIOUSLY_SELECTED")
            manifest = json.loads((output/"SHA256.json").read_bytes())["files"]
            for name, pin in manifest.items():
                self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(), pin)
            self.assertEqual(historical_compatibility()["current_gateway_compatibility"], "UNVERIFIED_NO_API_REQUESTS")


if __name__ == "__main__":
    unittest.main()
