"""Independent adversarial L1/V1 checks; no semantic oracle or real GT."""
import copy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import AuditError, PrivateAudit
from llmgnn_sara.sara3.evidence import EvidenceError, EvidenceSource, validate_claims, validate_result, quote_for_matching
from llmgnn_sara.sara3.pipeline import run_offline
from llmgnn_sara.downstream.frozen import plan_from_frozen

TEXT = "Neural networks learn useful representations from scientific papers."


def reply(label=1, abstain=False, evidence=None):
    return {"class_index": label, "abstain": abstain,
            "evidence": ["Neural networks learn useful representations"] if evidence is None else evidence}


class Verifier:
    offline = True

    def __init__(self, first=None, second=None, failure=None):
        self.first = reply() if first is None else first
        self.second = reply() if second is None else second
        self.failure, self.calls = failure, []

    def blind(self, request):
        self.calls.append(("blind", asdict(request)))
        if self.failure: raise self.failure
        return self.first

    def compare(self, request):
        self.calls.append(("compare", asdict(request)))
        # Deliberately try to corrupt the earlier mutable response object.
        self.first["evidence"] = ["mutated after blind"]
        return self.second


class L1Tests(unittest.TestCase):
    def source(self, name="target.text", field="text", text=TEXT):
        return EvidenceSource(name, field, text, hashlib.sha256(text.encode()).hexdigest())

    def claim(self, source=None):
        source = source or self.source()
        return {"source_id": source.source_id, "field": source.field,
                "source_sha256": source.sha256, "quote": "Neural networks learn useful representations"}

    def test_valid_source_quote_is_l1_only(self):
        self.assertEqual(len(validate_claims([self.claim()], (self.source(),))), 1)
        result = validate_result(reply(), TEXT)
        self.assertEqual(result["l1_status"], "PASS")
        self.assertNotIn("accepted_label", result)
        for sources in ([], (), (self.source(), self.source()), ("not a source",)):
            with self.assertRaisesRegex(EvidenceError, "L1_SOURCE_PROVENANCE_INVALID"):
                validate_claims([self.claim()], sources)

    def test_explicit_graph_source_requires_permission(self):
        graph = self.source("neighbor:42.text")
        with self.assertRaisesRegex(EvidenceError, "L1_UNKNOWN_SOURCE"):
            validate_claims([self.claim(graph)], (self.source(),))
        self.assertEqual(len(validate_claims([self.claim(graph)], (self.source(), graph))), 1)
        with self.assertRaises(EvidenceError): validate_result(reply(evidence=[self.claim(graph)]), TEXT)

    def test_source_field_hash_and_quote_failures(self):
        cases = (("source_id", "unknown", "L1_UNKNOWN_SOURCE"),
                 ("field", "context", "L1_REFERENCE_MISMATCH"),
                 ("source_sha256", "0"*64, "L1_REFERENCE_MISMATCH"),
                 ("quote", "Neural networks learn USEFUL representations", "L1_QUOTE_NOT_FOUND"))
        for key, value, code in cases:
            claim = self.claim(); claim[key] = value
            with self.subTest(code=code), self.assertRaisesRegex(EvidenceError, code):
                validate_claims([claim], (self.source(),))
        with self.assertRaisesRegex(EvidenceError, "L1_SOURCE_PROVENANCE_INVALID"):
            EvidenceSource("target.text", "text", TEXT, "0"*64)

    def test_empty_trivial_duplicate_and_malformed_evidence(self):
        for quotes in ([], [""], [" "], ["Neural"], ["a b"], [TEXT]*2, [1], ["x"*513]):
            with self.subTest(quotes=quotes), self.assertRaises(EvidenceError):
                validate_result(reply(evidence=quotes), TEXT)
        for claims in (None, {}, [dict(self.claim(), other=1)]):
            with self.assertRaises(EvidenceError): validate_claims(claims, (self.source(),))

    def test_complete_schema_classes_and_gt(self):
        for value in ([], None, "not JSON", {"class_index": 1}, dict(reply(), confidence=90)):
            with self.subTest(value=value), self.assertRaisesRegex(EvidenceError, "L1_SCHEMA_INVALID"):
                validate_result(value, TEXT)
        for label in (True, -1, 7, 1.0, None, "1"):
            with self.subTest(label=label), self.assertRaisesRegex(EvidenceError, "L1_CLASS_INVALID"):
                validate_result(reply(label), TEXT)
        for key in ("y", "fixed_y", "gt", "e0", "correctness"):
            class Poison:
                def __int__(self): raise AssertionError("GT decoded")
            with self.assertRaisesRegex(EvidenceError, "L1_GT_FIELD_FORBIDDEN"):
                validate_result(dict(reply(), **{key: Poison()}), TEXT)
            with self.assertRaisesRegex(EvidenceError, "L1_GT_FIELD_FORBIDDEN"):
                self.source(field=key)

    def test_abstention_is_strict_not_repaired(self):
        self.assertEqual(validate_result(reply(None, True, []), TEXT)["evidence"], ())
        for raw in (reply(1, True, []), reply(None, True, [TEXT]), reply(1, True, [TEXT])):
            before = copy.deepcopy(raw)
            with self.assertRaisesRegex(EvidenceError, "L1_ABSTENTION_CONTRADICTION"):
                validate_result(raw, TEXT)
            self.assertEqual(raw, before)

    def test_single_decorative_pair_preserves_original_payload_and_claim(self):
        quote = "Neural networks learn useful representations"
        for left, right in (("", ""), ('"', '"'), ('\u201c', '\u201d')):
            with self.subTest(wrapper=(left, right)):
                raw = reply(evidence=[left+quote+right]); before = copy.deepcopy(raw)
                result = validate_result(raw, TEXT)
                self.assertEqual(result["l1_status"], "PASS")
                self.assertEqual(result["evidence"], (raw["evidence"][0],))
                self.assertEqual(raw, before)
                claim = {**self.claim(), "quote": raw["evidence"][0]}
                self.assertEqual(validate_claims([claim], (self.source(),))[0][-1], raw["evidence"][0])

    def test_malformed_and_multiple_outer_wrappers_rejected_even_if_literal_in_source(self):
        quote = "Neural networks learn useful representations"
        values = ['"'+quote, quote+'"', '\u201c'+quote+'"', '"'+quote+'\u201d',
                  '\u201d'+quote+'\u201c', '""'+quote+'""', '\u201c\u201c'+quote+'\u201d\u201d',
                  '\u201c"'+quote+'"\u201d', '"\u201c'+quote+'\u201d"']
        for value in values:
            with self.subTest(wrapper=value), self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
                validate_result(reply(evidence=[value]), value)

    def test_no_content_edits_trimming_or_fuzzy_matching(self):
        for quote in ("Neural networks learn USEFUL representations", "Neural networks learn useful representations!",
                      "Neural  networks learn useful representations", " Neural networks learn useful representations",
                      "Neural\nnetworks learn useful representations", TEXT+" ",
                      "Neural networks learn fabricated representations"):
            with self.subTest(quote=quote), self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
                validate_result(reply(evidence=['\u201c'+quote+'\u201d']), TEXT)
        with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
            validate_result(reply(evidence=['\u201ccaf\u00e9 evidence\u201d']), 'cafe\u0301 evidence')

    def test_interior_quotes_punctuation_and_whitespace_preserved(self):
        quote = 'Scientific "topic" and \u201cmethod\u201d differ;  preserve\tspacing.'
        for left, right in (('"', '"'), ('\u201c', '\u201d')):
            wrapped = left+quote+right
            self.assertEqual(quote_for_matching(wrapped), quote)
            self.assertEqual(validate_result(reply(evidence=[wrapped]), quote)["evidence"], (wrapped,))

    def test_synthetic_excerpt_is_exact_and_avoids_cut_wrappers(self):
        from llmgnn_sara.evaluation.routing_experiment import synthetic_source_excerpt
        text = '\u201cA synthetic "topic" has  exact\tspacing and more content.'
        quote = synthetic_source_excerpt(text)
        self.assertIn(quote, text)
        self.assertIn('"topic" has  exact\tspacing', quote)
        self.assertEqual(validate_result(reply(evidence=[quote]), text)["l1_status"], "PASS")

    def test_wrapper_does_not_bypass_trivial_length_source_or_abstention_checks(self):
        for quote in ('""', '\u201ca b\u201d', '"'+"x"*511+'"'):
            with self.assertRaises(EvidenceError):
                validate_result(reply(evidence=[quote]), TEXT)
        with self.assertRaisesRegex(EvidenceError, "L1_ABSTENTION_CONTRADICTION"):
            validate_result(reply(None, True, ['"'+TEXT+'"']), TEXT)
        with self.assertRaisesRegex(EvidenceError, "L1_UNKNOWN_SOURCE"):
            validate_claims([{**self.claim(), "source_id": "unknown", "quote": '"'+TEXT+'"'}], (self.source(),))
        with self.assertRaisesRegex(EvidenceError, "L1_DUPLICATE_EVIDENCE"):
            validate_result(reply(evidence=[TEXT, '\u201c'+TEXT+'\u201d']), TEXT)
        for wrapped in ("'"+TEXT+"'", '\u00ab'+TEXT+'\u00bb', ' "'+TEXT+'" '):
            with self.assertRaisesRegex(EvidenceError, "L1_QUOTE_NOT_FOUND"):
                validate_result(reply(evidence=[wrapped]), TEXT)


class V1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit = PrivateAudit(Path(self.temp.name)/"private audit")
        self.pair = Pair(Annotation(9, 1, 95), Annotation(9, 1, 96), TEXT)

    def run_case(self, verifier, pair=None):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            return run_offline([pair or self.pair], 1, verifier=verifier, audit=self.audit)

    def records(self):
        return [self.audit.read(p.stem) for p in self.audit.root.glob("*.json")]

    def test_same_class_candidate_does_not_bypass_l2(self):
        report = self.run_case(Verifier())
        d = report["decisions"][0]
        self.assertEqual(d["reason"], "L2_NOT_ASSESSED")
        self.assertEqual((d["abstain"], d["accepted_label"], d["evidence"]), (True, None, []))
        self.assertFalse(d["accepted"])
        self.assertNotIn("Neural networks learn useful representations", json.dumps(d))

    def test_wrapped_evidence_does_not_change_payloads_arbitration_or_raw_audit(self):
        plain = self.run_case(Verifier())
        raw = reply(evidence=['\u201cNeural networks learn useful representations\u201d'])
        wrapped = self.run_case(Verifier(copy.deepcopy(raw), copy.deepcopy(raw)))
        self.assertEqual(plain["verifier_inputs"], wrapped["verifier_inputs"])
        self.assertEqual(plain["decisions"], wrapped["decisions"])
        self.assertIsNone(wrapped["decisions"][0]["accepted_label"])
        self.assertTrue(any(r.get("raw_response") == raw for r in self.records()))

    def test_immutable_blind_before_comparison_and_no_prior_fields(self):
        verifier = Verifier()
        before = copy.deepcopy(verifier.first)
        self.run_case(verifier)
        self.assertNotEqual(verifier.first, before)
        records = self.records()
        final = next(r for r in records if r["kind"] == "arbitration")
        blind = self.audit.read(final["blind_response_sha256"])
        self.assertEqual(blind["raw_response"], before)
        self.assertEqual([phase for phase, _ in verifier.calls], ["blind", "compare"])
        for key in ("historical_candidates", "confidence", "b1", "narrative_v0", "y"):
            self.assertNotIn(key, verifier.calls[0][1])

    def test_contradictions_rejected_and_raw_preserved_privately(self):
        raw = reply(None, True, [TEXT])
        report = self.run_case(Verifier(first=raw))
        self.assertEqual(report["decisions"][0]["reason"], "L1_ABSTENTION_CONTRADICTION")
        self.assertEqual(report["ledger"][0]["state"], "REJECTED")
        rejected = next(r for r in self.records() if r["kind"] == "response")
        self.assertEqual(rejected["raw_response"], raw)
        self.assertEqual(rejected["reason"], "L1_ABSTENTION_CONTRADICTION")
        self.assertEqual(len(report["verifier_inputs"]), 1)

    def test_third_classes_audit_only_never_remapped(self):
        for first, second, reason in ((6, 6, "THIRD_CLASS_PROPOSAL_ONLY"), (1, 6, "VERIFIER_CONFLICT")):
            report = self.run_case(Verifier(reply(first), reply(second)))
            d = report["decisions"][0]
            self.assertEqual(d["reason"], reason)
            self.assertIsNone(d["accepted_label"])
            self.assertIsNone(d["third_class_proposal"])
        proposals = [r["third_class_proposal"] for r in self.records() if r["kind"] == "arbitration"]
        self.assertIn(6, proposals)

    def test_valid_abstention_and_conflict(self):
        for verifier, reason in ((Verifier(reply(None, True, [])), "BLIND_ABSTENTION"),
                                 (Verifier(second=reply(None, True, [])), "COMPARISON_ABSTENTION"),
                                 (Verifier(second=reply(0)), "VERIFIER_CONFLICT")):
            d = self.run_case(verifier)["decisions"][0]
            self.assertEqual(d["reason"], reason)
            self.assertTrue(d["abstain"])
            self.assertEqual(d["evidence"], [])

    def test_timeout_audit_and_secret_safe_failure(self):
        report = self.run_case(Verifier(failure=TimeoutError("SECRET_SENTINEL")))
        self.assertEqual(report["decisions"][0]["reason"], "TIMEOUT_UNCERTAIN_NO_RETRY")
        self.assertEqual(report["ledger"][0]["state"], "UNCERTAIN")
        self.assertNotIn("SECRET_SENTINEL", json.dumps(report)+json.dumps(self.records()))
        for failure in (ValueError("SECRET_SENTINEL"), EvidenceError("SECRET_SENTINEL")):
            report = self.run_case(Verifier(failure=failure))
            self.assertEqual(report["decisions"][0]["reason"], "VERIFIER_FAILURE_UNCERTAIN")
            self.assertEqual(report["ledger"][0]["state"], "UNCERTAIN")
            self.assertNotIn("SECRET_SENTINEL", json.dumps(report)+json.dumps(self.records()))

    def test_audit_failure_blocks_comparison_and_acceptance(self):
        verifier = Verifier()
        with patch.object(self.audit, "write", side_effect=AuditError()):
            report = self.run_case(verifier)
        self.assertEqual(len(verifier.calls), 1)
        self.assertEqual(report["decisions"][0]["reason"], "AUDIT_UNAVAILABLE")

    def test_unavailable_audit_blocks_first_verifier_call(self):
        verifier = Verifier()
        with patch("llmgnn_sara.sara3.pipeline.PrivateAudit", side_effect=AuditError()):
            report = run_offline([self.pair], 1, verifier=verifier)
        self.assertEqual(verifier.calls, [])
        self.assertEqual(report["decisions"][0]["reason"], "AUDIT_UNAVAILABLE")

    def test_raw_tuple_evidence_is_not_silently_repaired(self):
        raw = reply(evidence=(TEXT,))
        report = self.run_case(Verifier(first=raw))
        self.assertEqual(report["decisions"][0]["reason"], "L1_SCHEMA_INVALID")
        self.assertEqual(report["mock_verifier_calls"], 1)

    def test_private_permissions_and_content_hashes(self):
        digest = self.audit.write({"raw_response": reply(), "reason": "SYNTHETIC"})
        path = self.audit.root/(digest+".json")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        self.assertEqual(self.audit.write(self.audit.read(digest)), digest)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaises(AuditError): PrivateAudit(Path(self.temp.name)/"web"/"export")

    def test_unsafe_existing_directory_is_rejected_not_repaired(self):
        root = Path(self.temp.name)/"unsafe synthetic empty directory"
        private = PrivateAudit(root)
        if os.name == "nt":
            from llmgnn_sara.sara3.audit import _restrict_windows
            _restrict_windows(root, "S-1-1-0")
        else:
            root.chmod(0o755)
        try:
            with self.assertRaises(AuditError): PrivateAudit(root)
        finally:
            if os.name == "nt": _restrict_windows(root, private.sid)
            else: root.chmod(0o700)

    def test_training_adapter_rejects_contradictory_or_reviewed_acceptance(self):
        class Dataset:
            def by_arm(self, arm): return ()
            predictions = ()
        decision = {"accepted": True, "training_class_index": 1, "accepted_label": 1,
                    "abstain": True, "evidence": []}
        with self.assertRaisesRegex(ValueError, "Contradictory"):
            plan_from_frozen(Dataset(), "sensitivity", "ce", accepted=[decision])
        decision.update(abstain=False, routed_for_review=True)
        with self.assertRaisesRegex(ValueError, "L2 semantic"):
            plan_from_frozen(Dataset(), "sensitivity", "ce", accepted=[decision])

    def test_pair_immutability_and_missing_text(self):
        before = repr(self.pair)
        self.run_case(Verifier())
        self.assertEqual(repr(self.pair), before)
        pair = Pair(self.pair.b1, self.pair.narrative_v0, "")
        verifier = Verifier()
        self.assertEqual(self.run_case(verifier, pair)["decisions"][0]["reason"], "MISSING_TARGET_TEXT")
        self.assertEqual(verifier.calls, [])
