"""Rich v1 structural/provenance validation; semantic assertions remain unassessed."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import AuditError, PrivateAudit
from llmgnn_sara.sara3.evidence import EvidenceError
from llmgnn_sara.sara3.inputs import RESPONSE_SCHEMA, canonical_bytes, verifier_input
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.sara3.rich_evidence import (RICH_RESPONSE_SCHEMA, RICH_VERSION,
                                            rich_verifier_input, target_source, validate_rich_result)

TEXT = "Neural networks learn representations. Auxiliary search methods are also discussed."
QUOTE = "Neural networks learn representations."
COUNTER = "Auxiliary search methods are also discussed."
ROOT = Path(__file__).resolve().parents[1]


def response(label=1):
    return {"schema_version": RICH_VERSION, "class_index": label, "abstain": False,
            "primary_topic": "A diagnostic hypothesis about representation learning.",
            "supporting_evidence": [{"source_id": "target.text", "quote": QUOTE,
                                     "claim": "SYNTHETIC_PRIVATE_CLAIM: the quotation relates to the proposed topic."}],
            "counter_evidence": [], "auxiliary_method_warning": None, "uncertainty_reason": None}


class RichValidationTests(unittest.TestCase):
    def validate(self, value):
        return validate_rich_result(value, (target_source(TEXT),))

    def test_valid_support_and_empty_counter(self):
        result = self.validate(response())
        self.assertEqual((result["l1_status"], result["l2_status"]), ("PASS", "NOT_ASSESSED"))
        self.assertEqual(result["rich_evidence"]["counter_evidence"], [])
        self.assertNotIn("accepted_label", result)

    def test_valid_counter_and_diagnostic_strings(self):
        raw = response()
        raw["counter_evidence"] = [{"source_id": "target.text", "quote": COUNTER,
                                   "claim": "An auxiliary method may distract from the primary topic."}]
        raw.update(auxiliary_method_warning="Method and topic may differ.", uncertainty_reason="Ambiguous emphasis.")
        result = self.validate(raw)
        self.assertEqual(result["rich_evidence"], {k: raw[k] for k in result["rich_evidence"]})

    def test_decorative_wrappers_shared_by_support_and_counter_without_rewriting(self):
        raw = response()
        raw["supporting_evidence"][0]["quote"] = '\u201c'+QUOTE+'\u201d'
        raw["counter_evidence"] = [{"source_id": "target.text", "quote": '"'+COUNTER+'"',
                                  "claim": "Synthetic counter claim, not semantic approval."}]
        before = copy.deepcopy(raw)
        result = self.validate(raw)
        self.assertEqual(raw, before)
        self.assertEqual(result["evidence"], (raw["supporting_evidence"][0]["quote"],))
        self.assertEqual(result["l2_status"], "NOT_ASSESSED")
        raw["counter_evidence"][0]["quote"] = '\u201cFabricated counter quotation.\u201d'
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
            self.validate(raw)

    def test_fabricated_counter_quote_rejected(self):
        raw = response()
        raw["counter_evidence"] = [{"source_id": "target.text", "quote": "A fabricated counter quotation.", "claim": "Counter claim"}]
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"): self.validate(raw)

    def test_unknown_sources_support_and_counter(self):
        for group in ("supporting_evidence", "counter_evidence"):
            raw = response()
            raw[group] = [{"source_id": "unknown", "quote": COUNTER, "claim": "A diagnostic statement."}]
            with self.subTest(group=group), self.assertRaisesRegex(EvidenceError, "L1_UNKNOWN_SOURCE"):
                self.validate(raw)

    def test_malformed_claims_types_extra_fields_and_missing_fields(self):
        for claim in (None, [], {}, 1, True, "", " ", "x"*2001):
            raw = response(); raw["supporting_evidence"][0]["claim"] = claim
            with self.subTest(claim_type=type(claim).__name__), self.assertRaises(EvidenceError): self.validate(raw)
        for field, value in (("primary_topic", []), ("primary_topic", " "), ("auxiliary_method_warning", True),
                             ("uncertainty_reason", {}), ("counter_evidence", None), ("class_index", True),
                             ("class_index", 7), ("supporting_evidence", []), ("abstain", 1)):
            raw = response(); raw[field] = value
            with self.subTest(field=field), self.assertRaises(EvidenceError): self.validate(raw)
        for field in response():
            raw = response(); del raw[field]
            with self.subTest(missing=field), self.assertRaises(EvidenceError): self.validate(raw)
        raw = response(); raw["supporting_evidence"][0]["field"] = "other"
        with self.assertRaises(EvidenceError): self.validate(raw)
        with self.assertRaises(EvidenceError): self.validate(dict(response(), confidence=100))

    def test_semantically_mismatched_claim_is_not_l2_validated(self):
        raw = response()
        raw["supporting_evidence"][0]["claim"] = "This quotation proves that the primary topic is genetic algorithms."
        result = self.validate(raw)
        self.assertEqual(result["l1_status"], "PASS")
        self.assertEqual(result["l2_status"], "NOT_ASSESSED")

    def test_abstention_no_silent_repair(self):
        raw = response(); raw.update(class_index=None, abstain=True, primary_topic=None,
                                     supporting_evidence=[], uncertainty_reason="Insufficient evidence.")
        self.assertEqual(self.validate(raw)["evidence"], ())
        for change in ({"class_index": 1}, {"primary_topic": "A proposed topic"},
                       {"counter_evidence": response()["supporting_evidence"]}):
            bad = copy.deepcopy(raw); bad.update(change); before = copy.deepcopy(bad)
            with self.assertRaisesRegex(EvidenceError, "L1_ABSTENTION_CONTRADICTION"): self.validate(bad)
            self.assertEqual(bad, before)
        raw["uncertainty_reason"] = None
        with self.assertRaises(EvidenceError): self.validate(raw)

    def test_existing_quote_rules_and_version_rejection(self):
        for quote in ("Neural", " ", "a b", "changed quotation"):
            raw = response(); raw["supporting_evidence"][0]["quote"] = quote
            with self.assertRaises(EvidenceError): self.validate(raw)
        raw = response(); raw["counter_evidence"] = copy.deepcopy(raw["supporting_evidence"])
        with self.assertRaisesRegex(EvidenceError, "L1_DUPLICATE_EVIDENCE"): self.validate(raw)
        raw = response(); raw["schema_version"] = "future-version"
        with self.assertRaisesRegex(EvidenceError, "L1_SCHEMA_VERSION_INVALID"): self.validate(raw)

    def test_total_evidence_limit_and_reference_types(self):
        raw = response()
        quotes = (TEXT, QUOTE, COUNTER, "Neural networks learn", "networks learn representations.")
        raw["supporting_evidence"] = [{"source_id": "target.text", "quote": q, "claim": "Diagnostic claim"} for q in quotes[:4]]
        raw["counter_evidence"] = [{"source_id": "target.text", "quote": quotes[4], "claim": "Diagnostic counter claim"}]
        with self.assertRaisesRegex(EvidenceError, "L1_EVIDENCE_MISSING_OR_MALFORMED"): self.validate(raw)
        for field in ("source_id", "quote"):
            raw = response(); raw["supporting_evidence"][0][field] = True
            with self.assertRaisesRegex(EvidenceError, "L1_CLAIM_SCHEMA_INVALID"): self.validate(raw)

    def test_gt_fields_rejected_without_decoding(self):
        class Poison:
            def __int__(self): raise AssertionError("GT decoded")
        raw = response(); raw["supporting_evidence"][0]["y"] = Poison()
        with self.assertRaisesRegex(EvidenceError, "L1_GT_FIELD_FORBIDDEN"): self.validate(raw)

    def test_schema_builder_isolated_from_legacy_and_caller_mutation(self):
        legacy = verifier_input(9, TEXT)
        old_schema = canonical_bytes(RESPONSE_SCHEMA)
        rich = rich_verifier_input(9, TEXT)
        self.assertEqual(rich["response_contract"], RICH_VERSION)
        self.assertEqual(rich["response_schema"], RICH_RESPONSE_SCHEMA)
        rich["response_schema"]["properties"]["primary_topic"]["maxLength"] = 1
        self.assertEqual(canonical_bytes(RESPONSE_SCHEMA), old_schema)
        self.assertEqual(verifier_input(9, TEXT), legacy)
        self.assertEqual(RICH_RESPONSE_SCHEMA["properties"]["primary_topic"]["maxLength"], 2000)


class RichPipelineTests(unittest.TestCase):
    def test_abstention_pipeline_normalization(self):
        raw = response(); raw.update(class_index=None, abstain=True, primary_topic=None,
                                     supporting_evidence=[], uncertainty_reason="Insufficient support.")
        class Verifier:
            offline = True
            def blind(self, request): return raw
            def compare(self, request): raise AssertionError("Abstention must stop comparison")
        pair = Pair(Annotation(9, 1, 95), Annotation(9, 1, 96), TEXT)
        with tempfile.TemporaryDirectory() as base:
            report = run_offline([pair], 1, verifier=Verifier(), audit=PrivateAudit(Path(base)/"abstain"),
                                 response_version=RICH_VERSION)
        d = report["decisions"][0]
        self.assertEqual((d["reason"], d["accepted_label"], d["evidence"]), ("BLIND_ABSTENTION", None, []))

    def test_private_audit_blind_boundary_and_no_acceptance(self):
        for label, reason in ((1, "L2_NOT_ASSESSED"), (6, "THIRD_CLASS_PROPOSAL_ONLY")):
            raw = response(label)
            class Verifier:
                offline = True
                def blind(self, request): return raw
                def compare(self, request): return response(label)
            pair = Pair(Annotation(9, 1, 95), Annotation(9, 1, 96), TEXT)
            with tempfile.TemporaryDirectory() as base:
                audit = PrivateAudit(Path(base)/"rich private audit")
                with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
                    report = run_offline([pair], 1, verifier=Verifier(), audit=audit, response_version=RICH_VERSION)
                decision = report["decisions"][0]
                self.assertEqual(decision["reason"], reason)
                self.assertEqual((decision["accepted_label"], decision["evidence"], decision["abstain"]), (None, [], True))
                self.assertNotIn("SYNTHETIC_PRIVATE_CLAIM", json.dumps(report))
                blind = report["verifier_inputs"][0]["payload"]
                self.assertEqual(blind["response_contract"], RICH_VERSION)
                self.assertNotIn("historical_candidates", blind)
                self.assertNotIn("confidence", blind)
                records = [audit.read(p.stem) for p in audit.root.glob("*.json")]
                stored = next(r for r in records if r.get("request_id") == "offline:9:blind")
                self.assertEqual(stored["raw_response"], raw)
                self.assertEqual(stored["validated"]["l2_status"], "NOT_ASSESSED")

    def test_fabricated_counter_is_audited_and_blocks_comparison(self):
        raw = response(); raw["counter_evidence"] = [{"source_id": "target.text", "quote": "Fabricated counter text.", "claim": "Counter"}]
        class Verifier:
            offline = True
            def blind(self, request): return raw
            def compare(self, request): raise AssertionError("Comparison must be blocked")
        pair = Pair(Annotation(9, 1, 95), Annotation(9, 1, 96), TEXT)
        with tempfile.TemporaryDirectory() as base:
            audit = PrivateAudit(Path(base)/"rich audit")
            report = run_offline([pair], 1, verifier=Verifier(), audit=audit, response_version=RICH_VERSION)
            self.assertEqual(report["decisions"][0]["reason"], "L1_QUOTE_NOT_FOUND")
            stored = audit.read(next(audit.root.glob("*.json")).stem)
            self.assertEqual(stored["raw_response"], raw)
            self.assertEqual(stored["l1_status"], "FAIL")

    def test_explicit_opt_in_only(self):
        class Verifier:
            offline = True
            def blind(self, request): return response()
        pair = Pair(Annotation(9, 1, 95), Annotation(9, 1, 96), TEXT)
        with tempfile.TemporaryDirectory() as base:
            report = run_offline([pair], 1, verifier=Verifier(), audit=PrivateAudit(Path(base)/"legacy"))
            self.assertEqual(report["decisions"][0]["reason"], "L1_SCHEMA_INVALID")
        with self.assertRaisesRegex(EvidenceError, "L1_SCHEMA_VERSION_INVALID"):
            run_offline([pair], 1, response_version="unknown")

    def test_audit_failure_still_prevents_comparison(self):
        class Verifier:
            offline = True
            def blind(self, request): return response()
            def compare(self, request): raise AssertionError("Comparison must be blocked")
        pair = Pair(Annotation(9, 1, 95), Annotation(9, 1, 96), TEXT)
        with tempfile.TemporaryDirectory() as base:
            audit = PrivateAudit(Path(base)/"rich audit")
            with patch.object(audit, "write", side_effect=AuditError()):
                result = run_offline([pair], 1, verifier=Verifier(), audit=audit, response_version=RICH_VERSION)
            self.assertEqual(result["decisions"][0]["reason"], "AUDIT_UNAVAILABLE")


@unittest.skipUnless((ROOT/".local_artifacts/authentic/b1_prompts.json").is_file(), "External authentic inputs not provided")
class RichCompatibilityTests(unittest.TestCase):
    def test_legacy_authentic_replay_matches_committed_report_exactly(self):
        from llmgnn_sara.sara3.replay import replay_authentic
        with tempfile.TemporaryDirectory() as base:
            actual = replay_authentic(ROOT/".local_artifacts/frozen", ROOT/".local_artifacts/authentic", Path(base)/"legacy replay")
        self.assertEqual(actual, json.loads((ROOT/"reports/authentic_l2_replay.json").read_bytes()))

    def test_p0_and_both_seals_unchanged(self):
        for name, digest in (("manifests/historical_p0.json", "7affacee222dbec3ecb5710b038968543c19d252190ee6eab76c5b03a4307410"),
                             (".local_artifacts/pilot-gapapi/SHA256.json", "29fa95c7d34f5826b628509e6bad2baced83ac986ebfbc7cadc4bb36d4c31b41"),
                             (".local_artifacts/pilot-gapapi/pilot/SHA256.json", "9fd65d82e3cab296afc503813b97b0c0af9e8f4dcb41cd0be1aa20ac34ef1f96")):
            path = ROOT/name
            if not path.is_file(): self.skipTest("Preserved seal not supplied")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
