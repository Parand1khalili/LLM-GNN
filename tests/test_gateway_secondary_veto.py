"""Small offline checks for post-freeze secondary evidence flags."""
import json
import unittest
from llmgnn_sara.sara3.gateway_secondary_veto import _flag_counts, analyze
from llmgnn_sara.sara3.gateway_closeout import freeze
from test_gateway_closeout import ReadOnlyCloseoutTests


def phase(*, counter=False, auxiliary=False, uncertain=False, topic="Topic",
          quote="source-evidence"):
    return {"rich_evidence": {"counter_evidence": (
                [{"quote": "opposing"}] if counter else []),
                "auxiliary_method_warning": "warning" if auxiliary else None,
                "uncertainty_reason": "uncertain" if uncertain else None,
                "primary_topic": topic,
                "supporting_evidence": [
                    {"source_id": "target.text", "quote": quote}]}}


class SecondaryVetoTests(unittest.TestCase):
    def test_counts_independent_secondary_flags_without_text(self):
        flags = _flag_counts(phase(counter=True, auxiliary=True),
                            phase(counter=False, uncertain=True,
                                  topic="Other", quote="different"))
        self.assertEqual(flags["either"],
                         {"counter_evidence": 1,
                          "auxiliary_method_warning": 1,
                          "uncertainty_reason": 1})
        self.assertEqual(flags["both_phases"],
                         {"counter_evidence": 0,
                          "auxiliary_method_warning": 0,
                          "uncertainty_reason": 0})
        self.assertEqual(flags["primary_topic_drift"], 1)
        self.assertEqual(flags["no_common_target_quote"], 1)
        self.assertNotIn("opposing", json.dumps(flags))
        self.assertNotIn("different", json.dumps(flags))

    def test_hash_bound_aggregate_matches_saved_fake_run(self):
        owner = ReadOnlyCloseoutTests("test_complete_no_redispatch_and_sealed_proposals")
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        summary = owner.closeout()
        sha = freeze(summary, owner.root)
        result = analyze(owner.root, sha, owner.execution["private_report_sha256"])
        expected = summary["automated_concordance"]["veto_or_abstain_reasons"]
        for reason, values in result["breakdown"].items():
            self.assertEqual(values["nodes"], expected.get(reason, 0))
        self.assertEqual(result["target_nodes"], sum(
            expected.get(k, 0) for k in result["breakdown"]))
        self.assertEqual(result["source_closeout_sha256"], sha)
        self.assertFalse(result["training_admission"])
        self.assertFalse(result["GT_accessed"])
        for sensitive in ("target.text", "raw_response", "supporting_evidence", "source-evidence"):
            self.assertNotIn(sensitive, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
