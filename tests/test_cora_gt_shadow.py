"""Synthetic-only post-freeze Cora GT scoring; never uses actual Cora labels."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import io
import json
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.evaluation import cora_gt_shadow as target
from llmgnn_sara.sara3.audit import PrivateAudit


def fixture():
    labels = [n % 7 for n in range(target.TRUE_COUNT)]
    selected = list(range(37))
    pairs = {n: SimpleNamespace(
        b1=SimpleNamespace(class_index=0),
        narrative_v0=SimpleNamespace(class_index=0)) for n in range(140)}
    reasons = (["COUNTER_EVIDENCE_UNRESOLVED"] * 11
               + ["THIRD_CLASS_DIAGNOSTIC_ONLY"] * 9
               + ["BLIND_ABSTENTION"] * 7
               + ["AUXILIARY_METHOD_WARNING"] * 6
               + ["VERIFIER_ABSTAINED"] * 2
               + ["PRIMARY_TOPIC_DRIFT"]
               + ["L1_DUPLICATE_EVIDENCE"])
    assert len(reasons) == 37
    decisions = []
    for n in range(140):
        reason = reasons[n] if n < 37 else "FROZEN_UNROUTED"
        blind = 1 if 11 <= n < 20 else 0
        comparison = blind
        if n >= 18 and n < 20:
            comparison = 0
        if 20 <= n < 27:
            blind = comparison = None
        if n in (33, 34, 36):
            comparison = None
        if n in range(11, 20):
            labels[n] = 1 if n < 15 else 0
        d = {"node_id": n,
             "b1_class_index": 0,
             "narrative_v0_class_index": 0,
             "routed_for_review": n < 37,
             "accepted": n >= 37,
             "training_class_index": None if n < 37 else 0,
             "l2_status": "NOT_ASSESSED" if n < 37 else "NOT_APPLICABLE_BASELINE_POLICY",
             "semantic_validation": "NOT_PERFORMED",
             "blind_class_index": blind if n < 37 else None,
             "comparison_class_index": comparison if n < 37 else None,
             "reason": reason}
        decisions.append(d)
    return selected, decisions, pairs, labels


class GTShadowTests(unittest.TestCase):
    def setUp(self):
        self.selected, self.decisions, self.pairs, self.labels = fixture()
        self.mock_socket = patch.object(socket.socket, "connect",
                                        side_effect=AssertionError("No network allowed"))
        self.mock_socket.start()
        self.addCleanup(self.mock_socket.stop)

    def score(self):
        return target.score(self.selected, self.decisions, self.pairs, self.labels,
                            freeze_sha256="f" * 64, graph_sha256=target.GRAPH_SHA256)

    def test_coverage_abstention_and_pairwise_truth_comparisons(self):
        before = deepcopy((self.selected, self.decisions, self.labels))
        result = self.score()
        self.assertEqual((self.selected, self.decisions, self.labels), before)
        self.assertEqual(result["routed_size"], 37)
        arms = result["all_routed"]["arms"]
        self.assertEqual([arms[a]["covered"] for a in target.ARMS], [37, 37, 30, 27])
        self.assertEqual([arms[a]["abstained_or_unavailable"] for a in target.ARMS],
                         [0, 0, 7, 10])
        for arm in target.ARMS:
            self.assertEqual(sum(x["support"] for x in arms[arm]["per_true_class"]), 37)
            self.assertEqual(sum(x["covered"] for x in arms[arm]["per_true_class"]),
                             arms[arm]["covered"])
        third = result["first_veto_strata"]["THIRD_CLASS_DIAGNOSTIC_ONLY"]
        self.assertEqual(third["n"], 9)
        self.assertEqual(third["arms"]["blind"]["correct"], 4)
        self.assertEqual(third["arms"]["b1"]["correct"], 5)
        self.assertEqual(third["paired"]["b1_vs_blind"]["net_correct_difference"], -1)
        self.assertEqual(result["third_class_phase_agree"]["n"], 7)
        self.assertEqual(result["first_veto_strata"]["COUNTER_EVIDENCE_UNRESOLVED"]["n"], 11)
        self.assertEqual(result["first_veto_strata"]["OTHER"]["n"], 17)
        self.assertEqual(result["provider_calls"], 0)
        self.assertTrue(result["ground_truth_accessed"])
        self.assertFalse(result["training_admission"])
        self.assertNotIn('"node_id"', json.dumps(result))
        self.assertNotIn('"truth"', json.dumps(result))

    def test_rejected_and_comparison_abstentions_are_distinguished(self):
        result = self.score()
        self.assertEqual(result["all_routed"]["arms"]["comparison"]["covered"], 27)
        bad = deepcopy(self.decisions)
        bad[33]["reason"] = "AUXILIARY_METHOD_WARNING"
        with self.assertRaises(ValueError):
            target.score(self.selected, bad, self.pairs, self.labels,
                         freeze_sha256="f" * 64, graph_sha256=target.GRAPH_SHA256)
        bad = deepcopy(self.decisions)
        bad[36]["comparison_class_index"] = 0
        with self.assertRaises(ValueError):
            target.score(self.selected, bad, self.pairs, self.labels,
                         freeze_sha256="f" * 64, graph_sha256=target.GRAPH_SHA256)

    def test_mutation_duplicate_missing_and_unadmitted_labels_fail_closed(self):
        for failure in ("duplicate", "selection", "baseline", "admission",
                        "reference", "extra", "bad_class"):
            d, selected, labels = deepcopy(self.decisions), list(self.selected), list(self.labels)
            if failure == "duplicate":
                d[38]["node_id"] = d[37]["node_id"]
            elif failure == "selection":
                selected[0] = 2707
            elif failure == "baseline":
                d[0]["b1_class_index"] = 6
            elif failure == "admission":
                d[0]["accepted"] = True
            elif failure == "reference":
                labels[0] = 99
            elif failure == "extra":
                d.append(deepcopy(d[0]))
            elif failure == "bad_class":
                d[12]["blind_class_index"] = 7
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                target.score(selected, d, self.pairs, labels,
                             freeze_sha256="f" * 64, graph_sha256=target.GRAPH_SHA256)

    def test_graph_fails_before_any_torch_pickle_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fake_original.pt"
            path.write_bytes(b"UNTRUSTED PICKLE, NO DESERIALIZATION")
            with self.assertRaises(ValueError):
                target._labels_from_original_graph(path)

    def test_private_write_only_and_sanitized_cli_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / ".local_artifacts" / "gt_score"
            audit = PrivateAudit(output)
            report = self.score()
            with patch.object(socket.socket, "connect",
                              side_effect=AssertionError("Network forbidden")):
                one = audit.write(report)
                self.assertEqual(audit.read(one), report)
                self.assertEqual(audit.write(report), one)
            self.assertTrue((output / (one + ".json")).is_file())
            with patch.object(target, "run", side_effect=ValueError(
                    "SENSITIVE NODE LABEL NEVER PRINT")), \
                 patch("sys.stderr", new_callable=io.StringIO) as err:
                args = ["--frozen-root", "none", "--authentic-root", "none",
                        "--run-root", "none", "--gateway-config", "none",
                        "--graph-file", "none", "--score-root", "none"]
                self.assertEqual(target.main(args), 1)
                self.assertEqual(json.loads(err.getvalue()), {"status": "FAIL_CLOSED"})

    def test_score_does_not_import_or_execute_arbitration_policy(self):
        with patch("llmgnn_sara.evaluation.cora_gt_shadow._labels_from_original_graph",
                   side_effect=AssertionError("No graph until frozen validation")):
            # Pure scorer has no graph, model, routing or training dependencies.
            self.assertEqual(self.score()["all_routed"]["n"], 37)


if __name__ == "__main__":
    unittest.main()
