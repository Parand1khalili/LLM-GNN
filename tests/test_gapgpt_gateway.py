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
    ENDPOINT, VERSION, AMENDED_OUTPUT_VERSION, DurableGapGPTVerifier, contract_from_dict, wire_for,
    worst_call_cost)
from llmgnn_sara.sara3.gateway_preflight import validate_batch_wire, VERSION as PREFLIGHT_VERSION
from llmgnn_sara.sara3.gateway_run import (
    SyntheticGapGPTHttp, approval_template, gateway_context,
    gateway_run, require_approval, scoped_owner_authorization,
    OWNER_PERMISSIONS, UNVERIFIED_PROVIDER_FIELDS,
    AMENDED_SCOPE_CONTEXT_SHA256, AMENDED_SCOPE_CONFIG_SHA256)
from llmgnn_sara.sara3.inputs import canonical_bytes
from llmgnn_sara.sara3.rich_evidence import rich_verifier_input_v2
from llmgnn_sara.sara3.gateway_diagnostics import diagnose
from llmgnn_sara.sara3.experiment import digest

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

    def test_authorized_scoped_batch_keeps_provider_unknown_and_needs_no_tariff(self):
        """Do not make false verification claims to permit owner-approved Batch."""
        from llmgnn_sara.sara3 import gateway_run as gateway
        expected = approval_template(self.data, "r0", 37, "sensitivity", self.config)
        with (patch.object(gateway, "APPROVED_SCOPE_CONTEXT_SHA256",
                           expected["execution_context_sha256"]),
              patch.object(gateway, "APPROVED_SCOPE_CONFIG_SHA256",
                           expected["gateway_contract_sha256"])):
            approval = scoped_owner_authorization(
                self.data, "r0", 37, "sensitivity", self.config)
            self.assertIsNone(require_approval(
                approval, self.data, "r0", 37, "sensitivity", self.config))
            for field in OWNER_PERMISSIONS:
                self.assertIs(approval[field], True)
            for field in UNVERIFIED_PROVIDER_FIELDS:
                self.assertIs(approval[field], False)
            self.assertEqual(approval["spend_cap_usd"], "0.40")
            # Changing policy scope, budget or config cannot auto-expand consent.
            with self.assertRaises(ValueError):
                scoped_owner_authorization(self.data, "r0", 36, "sensitivity",
                                           self.config)
            changed = deepcopy(self.config)
            changed["max_spend_usd"] = "0.50"
            with self.assertRaises(ValueError):
                scoped_owner_authorization(self.data, "r0", 37, "sensitivity",
                                           changed)

    def test_unverified_provider_fields_are_neither_required_true_nor_mislabelled(self):
        approval = approval_template(self.data, "r0", 37, "sensitivity", self.config)
        for name in OWNER_PERMISSIONS:
            approval[name] = True
        self.assertIsNone(require_approval(
            approval, self.data, "r0", 37, "sensitivity", self.config))
        for name in OWNER_PERMISSIONS:
            bad = deepcopy(approval)
            bad[name] = False
            with self.subTest(name=name), self.assertRaises(ValueError):
                require_approval(bad, self.data, "r0", 37, "sensitivity", self.config)
        for name in UNVERIFIED_PROVIDER_FIELDS:
            bad = deepcopy(approval)
            bad[name] = "false"
            with self.subTest(name=name), self.assertRaises(ValueError):
                require_approval(bad, self.data, "r0", 37, "sensitivity", self.config)
        bad = deepcopy(approval)
        bad["gateway_contract_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            require_approval(bad, self.data, "r0", 37, "sensitivity", self.config)

    def test_live_runner_requires_explicit_switch_before_dispatch(self):
        from llmgnn_sara.sara3 import runner, gateway_run as gateway
        from io import StringIO
        import contextlib
        argv = ["--mode", "live", "--frozen-root", "unused",
                "--authentic-root", "unused", "--output-root",
                str(self.root), "--gateway-config", str(CONFIG),
                "--router", "r0", "--budget", "37"]
        with (patch.object(runner, "load_project_inputs", return_value=self.data),
              patch.object(gateway, "gateway_run", side_effect=AssertionError(
                  "Live HTTP must not start without explicit switch"))):
            with contextlib.redirect_stderr(StringIO()):
                self.assertEqual(runner.main(argv), 1)

    def test_live_runner_explicit_switch_uses_single_scoped_authorization(self):
        from llmgnn_sara.sara3 import runner, gateway_run as gateway
        from io import StringIO
        import contextlib
        argv = ["--mode", "live", "--enable-real-dispatch",
                "--frozen-root", "unused", "--authentic-root", "unused",
                "--output-root", str(self.root), "--gateway-config",
                str(CONFIG), "--router", "r0", "--budget", "37"]
        fake_receipt = {"version": "sara.gapgpt.owner_batch_approval.v2"}
        with (patch.object(runner, "load_project_inputs", return_value=self.data),
              patch.object(gateway, "scoped_owner_authorization",
                           return_value=fake_receipt) as build,
              patch.object(gateway, "gateway_run", return_value={
                  "status": "BLOCKED_NO_AUTOMATIC_RETRY"}) as invoked):
            with contextlib.redirect_stdout(StringIO()):
                self.assertEqual(runner.main(argv), 2)
        build.assert_called_once_with(
            self.data, "r0", 37, "sensitivity", self.config)
        invoked.assert_called_once()
        self.assertIs(invoked.call_args.kwargs["fake"], False)
        self.assertIs(invoked.call_args.kwargs["approval"], fake_receipt)
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

    def test_reasoning_truncation_exact_512_token_diagnostic(self):
        """Never interpret all-reasoning length response as an L1 label."""
        class ReasoningExhausted:
            calls = 0
            def __call__(self, wire, key):
                self.calls += 1
                from llmgnn_sara.sara3.inputs import canonical_bytes
                return 200, canonical_bytes({
                    "id": "chatcmpl-reasoning-exhausted",
                    "model": "gpt-6-luna",
                    "choices": [{"finish_reason": "length",
                                 "message": {"role": "assistant", "content": ""}}],
                    "usage": {"prompt_tokens": 1522, "completion_tokens": 512,
                              "total_tokens": 2034,
                              "completion_tokens_details": {"reasoning_tokens": 512}}})
        transport = ReasoningExhausted()
        report = self.run_fake(transport)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(report["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertEqual(report["journal_states"], {"COMPLETED": 0,
                         "REJECTED": 1, "UNCERTAIN": 0})
        self.assertEqual(report["rejection_codes"], {"TRUNCATED_OR_NONFINAL": 1})
        self.assertEqual(report["provisional_count"], 0)
        self.assertEqual(report["unknown_billing_attempts"], 1)
        self.assertEqual(self.run_fake(SyntheticGapGPTHttp("gpt-6-luna"))["new_dispatches"], 0)

    def test_amended_output_contract_version_enforced_and_worst_cost(self):
        new_path = ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
        amended = json.loads(new_path.read_text(encoding="utf-8"))
        self.assertEqual(amended["version"], AMENDED_OUTPUT_VERSION)
        self.assertEqual(amended["max_tokens"], 4096)
        self.assertEqual(contract_from_dict(amended), amended)
        self.assertEqual(validate_batch_wire(self.data, "r0", 37, amended)[
            "declared_maximum_reservation_usd"], "0.3940352")
        self.assertEqual(amended["max_calls"], 74)
        self.assertEqual(amended["max_spend_usd"], "0.40")
        self.assertEqual(json.loads(wire_for(
            rich_verifier_input_v2(130, TEXT), amended))["max_tokens"], 4096)
        legacy_with_new_cap = deepcopy(self.config)
        legacy_with_new_cap["max_tokens"] = 4096
        with self.assertRaises(ValueError):
            contract_from_dict(legacy_with_new_cap)
        amended_with_old_cap = deepcopy(amended)
        amended_with_old_cap["max_tokens"] = 512
        with self.assertRaises(ValueError):
            contract_from_dict(amended_with_old_cap)
        amended_with_higher_cap = deepcopy(amended)
        amended_with_higher_cap["max_tokens"] = 8192
        with self.assertRaises(ValueError):
            contract_from_dict(amended_with_higher_cap)

    def test_amended_contract_must_never_reuse_historical_fake_journal(self):
        cfg = json.loads((ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
                         ).read_text(encoding="utf-8"))
        old = self.run_fake()
        self.assertEqual(old["journal_states"]["COMPLETED"], 74)
        fake = SyntheticGapGPTHttp("gpt-6-luna")
        with self.assertRaises(ValueError):
            self.run_fake(transport=fake, config=cfg)
        self.assertEqual(fake.dispatches, 0)
        separate_root = self.root.parent / "gateway_fake_amended"
        with patch.object(socket.socket, "connect",
                          side_effect=AssertionError("Network forbidden")):
            new = gateway_run(self.data, separate_root, router="r0",
                              budget=37, cohort="sensitivity", config=cfg,
                              fake=True, transport=fake)
        self.assertEqual(new["journal_states"]["COMPLETED"], 74)
        self.assertEqual(new["new_dispatches"], 74)
        self.assertNotEqual(new["gateway_context_sha256"], old["gateway_context_sha256"])

    def test_amended_owner_authorization_is_exact_and_provider_stays_unverified(self):
        from llmgnn_sara.sara3 import gateway_run as gateway
        from llmgnn_sara.sara3.experiment import digest
        cfg = json.loads((ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
                         ).read_text(encoding="utf-8"))
        self.assertEqual(digest(cfg), AMENDED_SCOPE_CONFIG_SHA256)
        expected = approval_template(self.data, "r0", 37, "sensitivity", cfg)
        with (patch.object(gateway, "AMENDED_SCOPE_CONTEXT_SHA256",
                           expected["execution_context_sha256"]),
              patch.object(gateway, "AMENDED_SCOPE_CONFIG_SHA256",
                           expected["gateway_contract_sha256"])):
            approval = scoped_owner_authorization(
                self.data, "r0", 37, "sensitivity", cfg)
            self.assertIsNone(require_approval(
                approval, self.data, "r0", 37, "sensitivity", cfg))
            self.assertEqual(approval["version"], "sara.gapgpt.owner_batch_approval.v2")
            self.assertEqual(approval["gateway_contract_sha256"],
                             expected["gateway_contract_sha256"])
            self.assertEqual(approval["execution_context_sha256"],
                             expected["execution_context_sha256"])
            for field in OWNER_PERMISSIONS:
                self.assertIs(approval[field], True)
            for field in UNVERIFIED_PROVIDER_FIELDS:
                self.assertIs(approval[field], False)
            # Consent to this amendment must not expand to new routing,
            # cohort, input hash, cost, model or token limit.
            for router, budget, cohort in (("r1", 37, "sensitivity"),
                                           ("r0", 36, "sensitivity"),
                                           ("r0", 37, "primary")):
                with self.subTest(router=router, budget=budget, cohort=cohort):
                    with self.assertRaises(ValueError):
                        scoped_owner_authorization(
                            self.data, router, budget, cohort, cfg)
            changed = deepcopy(cfg)
            changed["max_spend_usd"] = "0.50"
            with self.assertRaises(ValueError):
                scoped_owner_authorization(
                    self.data, "r0", 37, "sensitivity", changed)

    def test_amended_authorization_cannot_borrow_legacy_pinned_hashes(self):
        from llmgnn_sara.sara3 import gateway_run as gateway
        cfg = json.loads((ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
                         ).read_text(encoding="utf-8"))
        new_approval = approval_template(self.data, "r0", 37, "sensitivity", cfg)
        old_approval = approval_template(self.data, "r0", 37,
                                         "sensitivity", self.config)
        with (patch.object(gateway, "APPROVED_SCOPE_CONTEXT_SHA256",
                           new_approval["execution_context_sha256"]),
              patch.object(gateway, "APPROVED_SCOPE_CONFIG_SHA256",
                           new_approval["gateway_contract_sha256"])):
            with self.assertRaisesRegex(ValueError, "scope"):
                scoped_owner_authorization(self.data, "r0", 37,
                                           "sensitivity", cfg)
        for field in OWNER_PERMISSIONS:
            old_approval[field] = True
        with self.assertRaises(ValueError):
            require_approval(old_approval, self.data, "r0",
                             37, "sensitivity", cfg)

    def test_amendment_approval_receipt_persisted_before_attempt(self):
        from llmgnn_sara.sara3 import gateway_run as gateway
        from llmgnn_sara.sara3.gapgpt_live import (
            AMENDED_OUTPUT_VERSION, )
        cfg = json.loads((ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
                         ).read_text(encoding="utf-8"))
        expected = approval_template(self.data, "r0", 37, "sensitivity", cfg)
        with (patch.object(gateway, "AMENDED_SCOPE_CONTEXT_SHA256",
                           expected["execution_context_sha256"]),
              patch.object(gateway, "AMENDED_SCOPE_CONFIG_SHA256",
                           expected["gateway_contract_sha256"])):
            approval = scoped_owner_authorization(
                self.data, "r0", 37, "sensitivity", cfg)
        self.assertEqual(cfg["version"], AMENDED_OUTPUT_VERSION)
        import llmgnn_sara.sara3.gapgpt_live as live
        with (patch.object(socket.socket, "connect",
                           side_effect=AssertionError("Network forbidden")),
              patch.object(live, "post_once",
                           side_effect=TimeoutError("synthetic lost HTTP"))):
            result = gateway_run(self.data, self.root, router="r0",
                                 budget=37, cohort="sensitivity", config=cfg,
                                 fake=False, approval=approval,
                                 key="synthetic-ephemeral-key")
        self.assertEqual(result["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertEqual(result["journal_states"]["UNCERTAIN"], 1)
        self.assertEqual(result["attempted_calls"], 1)
        receipts = [json.loads(p.read_text(encoding="utf-8"))
                    for p in (self.root / "journal").glob("*.json")]
        owner_receipts = [r for r in receipts
                          if r.get("kind") == "gapgpt_owner_batch_authorization_v2"]
        self.assertEqual(len(owner_receipts), 1)
        self.assertEqual(owner_receipts[0]["scientific_amendment"],
                         "OWNER_APPROVED_512_TO_4096_AFTER_REASONING_TRUNCATION")
        self.assertEqual(owner_receipts[0]["approval"], approval)
        self.assertFalse(owner_receipts[0]["approval"]["current_gateway_prices_verified"])
        for p in (self.root / "journal").glob("*.json"):
            self.assertNotIn(b"synthetic-ephemeral-key", p.read_bytes())

    def test_old_scope_authorization_does_not_approve_amended_contract(self):
        cfg = json.loads((ROOT / "configs/gapgpt_rich_v2_output4096_proposed.json"
                         ).read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "scope"):
            scoped_owner_authorization(self.data, "r0", 37, "sensitivity", cfg)

    def test_read_only_diagnostic_counts_duplicate_without_private_text(self):
        class DuplicateEvidenceTransport:
            dispatches = 0
            def __call__(self, wire, key):
                self.dispatches += 1
                status, raw = SyntheticGapGPTHttp("gpt-6-luna")(wire, key)
                envelope = json.loads(raw)
                result = json.loads(envelope["choices"][0]["message"]["content"])
                if result["abstain"]:
                    raise AssertionError("This fixture must have exact source support")
                support = result["supporting_evidence"][0]
                result["supporting_evidence"] = [support, dict(support)]
                envelope["choices"][0]["message"]["content"] = (
                    canonical_bytes(result).decode("utf-8"))
                return status, canonical_bytes(envelope)
        transport = DuplicateEvidenceTransport()
        stopped = self.run_fake(transport)
        self.assertEqual(stopped["status"], "BLOCKED_NO_AUTOMATIC_RETRY")
        self.assertEqual(stopped["rejection_codes"], {"L1_DUPLICATE_EVIDENCE": 1})
        self.assertEqual(transport.dispatches, 1)
        _, ctx = gateway_context(self.data, "r0", 37, "sensitivity",
                                 self.config, fake=True)
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (self.root / "journal").iterdir() if p.is_file()}
        report = diagnose(self.root, expected_context_sha256=digest(ctx))
        self.assertTrue(report["read_only"])
        self.assertTrue(report["journal_context_verified"])
        self.assertEqual(report["states"],
                         {"COMPLETED": 0, "REJECTED": 1, "UNCERTAIN": 0})
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(len(report["rejected_receipts"]), 1)
        item = report["rejected_receipts"][0]
        self.assertEqual(item["reject_code"], "L1_DUPLICATE_EVIDENCE")
        self.assertEqual((item["rich_json_parseable"],
                          item["supporting_evidence_count"],
                          item["duplicate_pair_count"]),
                         (True, 2, 1))
        self.assertEqual(item["duplicate_pair_kinds"],
                         {"supporting_then_supporting": 1})
        serialized = json.dumps(report)
        self.assertNotIn(TEXT, serialized)
        self.assertNotIn("Paper identifier", serialized)
        self.assertNotIn("raw_hex", serialized)
        self.assertEqual(before, {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (self.root / "journal").iterdir() if p.is_file()})
        # Inspecting cannot replay, retry, or change terminal rejected state.
        self.assertEqual(self.run_fake()["new_dispatches"], 0)

    def test_rejected_receipt_diagnostic_refuses_wrong_scope_and_tampering(self):
        def duplicate(wire, key):
            status, raw = SyntheticGapGPTHttp("gpt-6-luna")(wire, key)
            envelope = json.loads(raw)
            result = json.loads(envelope["choices"][0]["message"]["content"])
            result["supporting_evidence"].append(
                dict(result["supporting_evidence"][0]))
            envelope["choices"][0]["message"]["content"] = (
                canonical_bytes(result).decode("utf-8"))
            return status, canonical_bytes(envelope)
        self.assertEqual(self.run_fake(duplicate)["journal_states"]["REJECTED"], 1)
        _, ctx = gateway_context(self.data, "r0", 37, "sensitivity",
                                 self.config, fake=True)
        with self.assertRaisesRegex(ValueError, "binding"):
            diagnose(self.root, expected_context_sha256="0" * 64)
        import sqlite3
        db = self.root / "journal" / "fixture_journal.sqlite"
        with sqlite3.connect(db) as conn:
            receipt, = conn.execute(
                "SELECT receipt FROM intents WHERE state='REJECTED'"
            ).fetchone()
        path = self.root / "journal" / (receipt + ".json")
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash"):
            diagnose(self.root, expected_context_sha256=digest(ctx))

    def test_budget_reservation_rejected_before_any_journal_or_dispatch(self):
        cfg = deepcopy(self.config)
        cfg["max_spend_usd"] = "0.000001"
        fake = SyntheticGapGPTHttp(cfg["model"])
        with self.assertRaisesRegex(ValueError, "Worst-case declared reservation"):
            self.run_fake(transport=fake, config=cfg)
        self.assertEqual(fake.dispatches, 0)
        self.assertFalse(self.root.exists())

    def test_budget_exact_rejects_invalid_values(self):
        for key, value in (("version", []), ("version", "unknown"),
                           ("temperature", .5), ("max_tokens", 0),
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
