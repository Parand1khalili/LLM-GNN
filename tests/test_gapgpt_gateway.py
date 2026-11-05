"""GapGPT fake-wire integration and fail-closed live admission; never paid HTTP."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llmgnn_sara.sara2.policy import Annotation, Pair
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.gapgpt_live import (
    ENDPOINT, VERSION, DurableGapGPTVerifier, contract_from_dict, wire_for,
    worst_call_cost)
from llmgnn_sara.sara3.gateway_preflight import validate_batch_wire, VERSION as PREFLIGHT_VERSION
from llmgnn_sara.sara3.gateway_run import (
    SyntheticGapGPTHttp, approval_template, gateway_context,
    gateway_run, require_approval)
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.rich_evidence import rich_verifier_input_v2

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/gapgpt_rich_v2_proposed.json"
TEXT = ("Bayesian inference uses Gaussian process priors and posterior estimation "
        "to characterize probabilistic learning systems. "
        "This paper examines the theoretical properties of the proposed models. ")


def sample_rows():
    return tuple(Pair(
        Annotation(i, i % 7, 90),
        Annotation(i, (i + (i % 4 == 0)) % 7, 87),
        TEXT + f"Paper identifier {i}, purely synthetic diagnostic text.")
        for i in range(140))


def inputs(rows=None):
    class DummyFrozen:
        def by_arm(self, name):
            return ()
    return SimpleNamespace(pairs=rows or sample_rows(), provenance=(), frozen=DummyFrozen())


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.data = inputs()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / ".local_artifacts" / "gateway_fake"

    def run_fake(self, transport=None, config=None):
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            return gateway_run(self.data, self.root, router="r0", budget=37,
                               cohort="sensitivity", config=config or self.config,
                               fake=True, transport=transport)

    def test_real_fake_http_140_nodes_persist_resume_and_plan(self):
        first = self.run_fake()
        second = self.run_fake()
        self.assertEqual(first["status"], "COMPLETE_FAKE_HTTP")
        self.assertEqual((first["selected_count"], first["denominator"]), (37, 140))
        self.assertEqual((first["new_dispatches"], second["new_dispatches"]), (74, 0))
        self.assertEqual((first["successful_replays"], second["successful_replays"]), (0, 74))
        self.assertEqual(first["journal_states"]["COMPLETED"], 74)
        self.assertEqual(first["private_report_sha256"], second["private_report_sha256"])
        self.assertEqual(first["private_plan_sha256"], second["private_plan_sha256"])
        self.assertEqual(first["plan_status"], "PLAN_ONLY_NO_TRAINING")
        self.assertTrue(first["no_training_label_for_routed_proposals"])
        self.assertEqual((first["GT_accessed"], first["training_runs"]), (False, 0))
        self.assertEqual(first["usage"]["completion_tokens"], 74 * 256)
        self.assertEqual(sum(first["provisional_class_distribution"].values()),
                         first["provisional_count"])

    def test_entire_cohort_wire_preflight_is_deterministic_and_local_only(self):
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            first = validate_batch_wire(self.data, "r0", 37, self.config)
            second = validate_batch_wire(self.data, "r0", 37, self.config)
        self.assertEqual(first, second)
        self.assertEqual(first["version"], PREFLIGHT_VERSION)
        self.assertEqual((first["selected_count"], first["maximum_conditional_calls"]),
                         (37, 74))
        self.assertLess(first["largest_possible_wire_bytes"], 32768)
        self.assertEqual(first["declared_maximum_reservation_usd"], "0.2614272")
        self.assertEqual(first["max_spend_usd"], "0.40")
        self.assertEqual(first["max_tokens_requested"], 512)
        self.assertIn("RICH_JSON_COMPLETENESS_WITH_MAX_TOKENS",
                      first["external_checks_not_verified"])
        self.assertEqual(first["provider_calls"], 0)
        self.assertFalse(first["GT_accessed"])

    def test_input_wire_too_large_fails_before_creating_private_journal(self):
        cfg = deepcopy(self.config)
        cfg["max_input_tokens"] = 100
        fake = SyntheticGapGPTHttp(cfg["model"])
        with self.assertRaisesRegex(ValueError, "conservative byte-size input cap"):
            self.run_fake(transport=fake, config=cfg)
        self.assertEqual(fake.dispatches, 0)
        self.assertFalse(self.root.exists())

    def test_provider_returned_revision_model_is_reported_exactly(self):
        revision = "gpt-6-luna-2026-09-22"
        report = self.run_fake(SyntheticGapGPTHttp(revision))
        self.assertEqual(report["status"], "COMPLETE_FAKE_HTTP")
        self.assertEqual(report["returned_models"], {revision: 74})
        self.assertEqual(report["requested_model"], "gpt-6-luna")
        self.assertEqual(report["unknown_billing_attempts"], 0)
        self.assertEqual(report["verified_usage_scope"],
                         "COMPLETED_PHASES_ONLY_NOT_ALL_ATTEMPTS")

    def test_response_mismatch_reason_is_durable_and_cost_unknown(self):
        def invalid(wire, key):
            status, raw = SyntheticGapGPTHttp(self.config["model"])(wire, key)
            obj = json.loads(raw)
            obj["model"] = "unapproved-gateway-model"
            return status, canonical_bytes(obj)
        report = self.run_fake(invalid)
        self.assertEqual(report["rejection_codes"], {"RETURNED_MODEL_MISMATCH": 1})
        self.assertEqual(report["unknown_billing_attempts"], 1)
        self.assertEqual(report["usage"]["prompt_tokens"], 0)
        self.assertEqual(report["journal_states"]["REJECTED"], 1)
        report2 = self.run_fake()
        self.assertEqual(report2["new_dispatches"], 0)
        self.assertEqual(report2["rejection_codes"], report["rejection_codes"])

    def test_output_limit_and_inconsistent_provider_usage_fail_closed(self):
        variants = (
            ("TRUNCATED_OR_NONFINAL", lambda e: e["choices"][0].update(finish_reason="length")),
            ("PROVIDER_USAGE_MISSING", lambda e: e.pop("usage")),
            ("PROVIDER_USAGE_OVER_CAP", lambda e: e["usage"].update(completion_tokens=513)),
            ("PROVIDER_TOTAL_TOKENS_CONFLICT", lambda e: e["usage"].update(total_tokens=1)),
        )
        for reason, change in variants:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                self.root = Path(tmp) / ".local_artifacts" / "bad_response"
                def broken(wire, key):
                    code, body = SyntheticGapGPTHttp(self.config["model"])(wire, key)
                    envelope = json.loads(body)
                    change(envelope)
                    return code, canonical_bytes(envelope)
                report = self.run_fake(broken)
                self.assertEqual(report["rejection_codes"], {reason: 1})
                self.assertEqual(report["unknown_billing_attempts"], 1)
                self.assertEqual(report["new_dispatches"], 1)

    def test_report_shape_preserves_previous_successful_fake_receipts(self):
        first = self.run_fake()
        # Session-level returned-model diagnostics do not alter scientific report.
        second = self.run_fake()
        self.assertEqual(first["private_report_sha256"], second["private_report_sha256"])
        self.assertEqual(first["returned_models"], {"gpt-6-luna": 74})
        self.assertEqual(second["returned_models"], first["returned_models"])
        self.assertEqual(first["rejection_codes"], {})

    def test_wire_preflight_blind_cannot_leak_historical_candidates(self):
        payload = rich_verifier_input_v2(130, TEXT)
        wire = wire_for(payload, self.config)
        decoded = json.loads(wire)
        blind = json.loads(decoded["messages"][0]["content"])
        self.assertEqual(decoded["temperature"], 1)
        self.assertEqual(decoded["max_tokens"], 512)
        self.assertNotIn("historical_candidates", blind)
        self.assertNotIn("blind_class_index", blind)
        self.assertEqual(decoded["model"], "gpt-6-luna")

    def test_missing_or_forged_approval_rejected_before_paid_send(self):
        expected = approval_template(self.data, "r0", 37, "sensitivity", self.config)
        self.assertTrue(all(expected[k] is False for k in (
            "data_sharing_approved", "spend_approved", "explicit_batch_dispatch_approved")))
        with self.assertRaises(ValueError):
            require_approval(expected, self.data, "r0", 37, "sensitivity", self.config)
        with self.assertRaises(ValueError):
            gateway_run(self.data, self.root, router="r0", budget=37,
                        cohort="sensitivity", config=self.config, fake=False,
                        approval=expected, key="fake-key-no-network")
        self.assertFalse(self.root.exists())

    def test_exact_positive_owner_approval_is_bound_but_never_sends_http(self):
        approval = approval_template(self.data, "r0", 37, "sensitivity", self.config)
        for field, value in list(approval.items()):
            if type(value) is bool:
                approval[field] = True
        self.assertIsNone(require_approval(
            approval, self.data, "r0", 37, "sensitivity", self.config))
        changed = deepcopy(self.config)
        changed["max_spend_usd"] = "0.50"
        with self.assertRaises(ValueError):
            require_approval(approval, self.data, "r0", 37, "sensitivity", changed)
        with self.assertRaises(ValueError):
            require_approval(approval, self.data, "r0", 36, "sensitivity", self.config)
        # The complete approval alone does not dispatch: credential is still required.
        with patch.dict("os.environ", {"GAPGPT_API_KEY": ""}):
            with self.assertRaises(ValueError):
                gateway_run(self.data, self.root, router="r0", budget=37,
                            cohort="sensitivity", config=self.config, fake=False,
                            approval=approval)
        self.assertFalse(self.root.exists())

    def test_contract_change_binds_journal_and_disables_dispatch(self):
        first = self.run_fake()
        cfg = deepcopy(self.config)
        cfg["input_usd_per_million"] = "0.11"
        with self.assertRaises(ValueError):
            self.run_fake(config=cfg)
        self.assertEqual(self.run_fake()["new_dispatches"], 0)

    def test_http_failure_persists_rejected_and_no_retry(self):
        class BadHTTP:
            calls = 0
            def __call__(self, wire, key):
                self.calls += 1
                return 503, b'{"error":{"message":"failed"}}'
        t = BadHTTP()
        first = self.run_fake(transport=t)
        self.assertEqual(t.calls, 1)
        self.assertEqual(first["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertEqual(first["journal_states"]["REJECTED"], 1)
        good = SyntheticGapGPTHttp("gpt-6-luna")
        second = self.run_fake(transport=good)
        self.assertEqual(good.dispatches, 0)
        self.assertEqual(second["journal_states"]["REJECTED"], 1)

    def test_unknown_timeout_is_not_automatically_resent(self):
        class Timeout:
            calls = 0
            def __call__(self, wire, key):
                self.calls += 1
                raise TimeoutError("Fake simulated provider timeout")
        transport = Timeout()
        first = self.run_fake(transport=transport)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(first["journal_states"]["UNCERTAIN"], 1)
        good = SyntheticGapGPTHttp("gpt-6-luna")
        second = self.run_fake(transport=good)
        self.assertEqual(good.dispatches, 0)
        self.assertEqual(second["new_dispatches"], 0)

    def test_wrong_returned_model_is_rejected_and_stored(self):
        bad = SyntheticGapGPTHttp("unapproved-upstream-alias")
        result = self.run_fake(bad)
        self.assertEqual(bad.dispatches, 1)
        self.assertEqual(result["journal_states"]["REJECTED"], 1)
        self.assertIsNone(result["private_plan_sha256"])

    def test_missing_usage_and_finish_reason_are_fail_closed(self):
        for mutate in (lambda value: value.pop("usage"),
                       lambda value: value["choices"][0].update(finish_reason="length")):
            with self.subTest(mutate=mutate):
                with tempfile.TemporaryDirectory() as temp:
                    self.root = Path(temp) / ".local_artifacts" / "bad_envelope"
                    good = SyntheticGapGPTHttp("gpt-6-luna")
                    def broken(wire, key):
                        status, raw = good(wire, key)
                        value = json.loads(raw)
                        mutate(value)
                        return 200, canonical_bytes(value)
                    report = self.run_fake(broken)
                    self.assertEqual(report["journal_states"]["REJECTED"], 1)
                    self.assertEqual(good.dispatches, 1)

    def test_credential_echo_redacted_not_saved(self):
        class Echo:
            def __call__(self, wire, key):
                return 200, canonical_bytes({"credentials_echo": key})
        report = self.run_fake(Echo())
        self.assertEqual(report["journal_states"]["REJECTED"], 1)
        journal = self.root / "journal"
        for path in journal.glob("*.json"):
            self.assertNotIn(b"synthetic-local-key-unknown", path.read_bytes())

    def test_budget_reservation_rejected_before_any_journal_or_dispatch(self):
        cfg = deepcopy(self.config)
        cfg["max_spend_usd"] = "0.000001"
        fake = SyntheticGapGPTHttp(cfg["model"])
        with self.assertRaisesRegex(ValueError, "Worst-case declared reservation"):
            self.run_fake(transport=fake, config=cfg)
        self.assertEqual(fake.dispatches, 0)
        self.assertFalse(self.root.exists())

    def test_budget_exact_rejects_invalid_values(self):
        for key, value in (("temperature", .5), ("max_tokens", 0),
                           ("max_calls", 75), ("max_spend_usd", "-1"),
                           ("input_usd_per_million", "nan"),
                           ("endpoint", "https://untrusted.site/v1/chat/completions"),
                           ("retention_status", "ZERO_DATA_RETENTION")):
            with self.subTest(key=key):
                bad = deepcopy(self.config)
                bad[key] = value
                with self.assertRaises(ValueError):
                    contract_from_dict(bad)

    def test_fake_mode_never_reads_api_key_or_accepts_live_approval(self):
        with patch.dict("os.environ", {"GAPGPT_API_KEY": "fake-test-environment-key"}):
            with self.assertRaises(ValueError):
                gateway_run(self.data, self.root, router="r0", budget=37,
                    cohort="sensitivity", config=self.config, fake=True,
                    key="fake-test-environment-key")
        result = self.run_fake()
        self.assertEqual(result["mode"], "FAKE_HTTP")

    def test_comparison_prerequisite_from_separate_journal_required(self):
        from llmgnn_sara.sara3.pipeline import ComparisonRequest
        selected, context = gateway_context(
            self.data, "r0", 37, "sensitivity", self.config, fake=True)
        verifier = DurableGapGPTVerifier(
            self.config, context, PrivateAudit(self.root / "journal"),
            transport=SyntheticGapGPTHttp(self.config["model"]),
            key="synthetic-local-key-unknown", authorized_fake=True)
        pair = next(p for p in self.data.pairs if p.node_id == selected[0])
        with self.assertRaises(ValueError):
            verifier.compare(ComparisonRequest(pair.node_id, pair.text,
                tuple(sorted({pair.b1.class_index, pair.narrative_v0.class_index})), 6,
                neighborhood=pair.neighborhood))


if __name__ == "__main__":
    unittest.main()
