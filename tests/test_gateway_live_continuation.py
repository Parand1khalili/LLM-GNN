"""Actual live adapter tests use the existing synthetic HTTP boundary only."""
import hashlib
import json
from pathlib import Path
import socket
from unittest import TestCase
from unittest.mock import patch

import llmgnn_sara.sara3.gateway_run as gateway
import llmgnn_sara.sara3.gateway_continuation as continuation
import llmgnn_sara.sara3.gateway_live_continuation as live
from test_gateway_amendment import AmendmentTests
from llmgnn_sara.sara3.experiment import digest
from llmgnn_sara.sara3.gateway_run import SyntheticGapGPTHttp


class LiveContinuationTests(TestCase):
    def setUp(self):
        self.fixture = AmendmentTests("test_scope_budget_and_amendment_fail_closed")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.addCleanup(self.fixture.doCleanups)
        self.data = self.fixture.rows
        self.config = self.fixture.cfg
        _, context = gateway.gateway_context(
            self.data, "r0", 37, "sensitivity", self.config, fake=False)
        self.context_sha = digest(context)
        self.amendment = {"version": "test-amendment"}
        self.approval = {
            "version": live.APPROVAL_VERSION,
            "amendment_sha256": digest(self.amendment),
            "execution_context_sha256": self.context_sha,
            "gateway_contract_sha256": digest(self.config),
            "original_intents": 53,
            "maximum_new_calls": 16,
            "maximum_cumulative_calls": 69,
            "max_spend_usd": self.config["max_spend_usd"],
            "data_sharing_approved": True,
            "spend_approved": True,
            "explicit_continuation_dispatch_approved": True,
        }
        original = gateway.gateway_context
        with patch.object(
                gateway, "gateway_context",
                side_effect=lambda *a, **k: original(*a, **{**k, "fake": False})):
            self.historical = self.fixture.historical_53()
        self.allowed = tuple(self.historical["not_attempted_after_halt_node_ids"])
        self.before = self.fixture.files()

    def _admit(self, inputs, root, *, config, amendment, fake=False):
        report = continuation.inspect(
            inputs, root, config=config,
            expected_context_sha256=self.context_sha, fake=False)
        if (report["original_intents"], report["completed_replayed_and_l1_verified"],
                report["rejected_preserved"]) != (53, 52, 1):
            raise ValueError("Unexpected historical fixture")
        return report

    def _run(self, transport):
        with (patch.object(live, "FROZEN_CONTEXT_SHA256", self.context_sha),
              patch.object(live, "FROZEN_CONTRACT_SHA256", digest(self.config)),
              patch.object(live, "FROZEN_BLINDS", self.allowed),
              patch.object(live, "amendment_preflight", side_effect=self._admit),
              patch.object(socket.socket, "connect",
                           side_effect=AssertionError("Direct networking prohibited")),
              ):
            def fake_http(wire, key, *, target):
                return transport(wire, key)
            with patch("llmgnn_sara.sara3.gapgpt_live.post_once", fake_http):
                return live.execute(
                    self.data, self.fixture.root, config=self.config,
                    amendment=self.amendment, approval=self.approval,
                    key="synthetic-transport-key-not-real")

    def test_live_path_dispatches_only_sixteen_and_restart_replays(self):
        transport = SyntheticGapGPTHttp("gpt-6-luna")
        result = self._run(transport)
        self.assertEqual(result["new_dispatches_this_invocation"], 16)
        self.assertEqual(result["new_intents_total"], 16)
        self.assertEqual(result["cumulative_intents"], 69)
        self.assertEqual(result["new_states"]["COMPLETED"], 16)
        self.assertEqual(transport.dispatches, 16)
        self.assertEqual(self.before, self.fixture.files())
        second = SyntheticGapGPTHttp("gpt-6-luna")
        result2 = self._run(second)
        self.assertEqual(result2["new_dispatches_this_invocation"], 0)
        self.assertEqual(result2["new_intents_total"], 16)
        self.assertEqual(second.dispatches, 0)
        self.assertEqual(self.before, self.fixture.files())

    def test_timeout_halts_and_refuses_restart(self):
        def fail(wire, key, *, target="account-panel-temperature1"):
            raise TimeoutError("synthetic timeout")
        first = self._run(fail)
        self.assertEqual(first["status"], "HALTED_NO_AUTOMATIC_RETRY")
        self.assertEqual(first["new_states"]["UNCERTAIN"], 1)
        with self.assertRaises(ValueError):
            self._run(SyntheticGapGPTHttp("gpt-6-luna"))
        self.assertEqual(self.before, self.fixture.files())

    def test_owner_approval_is_new_and_exact(self):
        with self.assertRaises(ValueError):
            live.require_continuation_approval({}, self.amendment, self.config)
        with patch.object(live, "FROZEN_CONTEXT_SHA256", self.context_sha), patch.object(
                live, "FROZEN_CONTRACT_SHA256", digest(self.config)):
            live.require_continuation_approval(
                self.approval, self.amendment, self.config)
            with self.assertRaises(ValueError):
                live.require_continuation_approval(
                    {**self.approval, "maximum_new_calls": 17},
                    self.amendment, self.config)
            with self.assertRaises(ValueError):
                live.require_continuation_approval(
                    {**self.approval, "spend_approved": False},
                    self.amendment, self.config)
