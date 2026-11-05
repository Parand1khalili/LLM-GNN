"""Fail-closed GapGPT Rich Prompt V2 gateway, with injectable one-shot HTTP.

This is NOT an inference approval or a semantic L2 validator. No retries, no
redirects, no proxy, no automatic reconciliation and no GCN admission.
"""
from contextlib import closing
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

from ..pilot.canary import post_once, strict_json
from .audit import PrivateAudit
from .durable_fixture import DurableOfflineFixtureVerifier
from .evidence import EvidenceError
from .experiment import digest
from .inputs import canonical_bytes
from .rich_evidence import RICH_PROMPT_V2, RICH_VERSION, rich_verifier_input_v2
from .rich_evidence import target_source, validate_rich_result

VERSION = "sara.gapgpt.rich_v2.gateway.v1"
AMENDED_OUTPUT_VERSION = "sara.gapgpt.rich_v2.gateway.v2"
# Exact allowable output caps are version-bound. A new amount always needs
# an explicit new contract, isolated journal and separately reviewed scope.
OUTPUT_CAP_BY_VERSION = {VERSION: 512, AMENDED_OUTPUT_VERSION: 4096}
JOURNAL_VERSION = "sara.gapgpt.rich_v2.journal.v1"
ENDPOINT = "https://api.gapgpt.app/v1/chat/completions"
MAX_BODY = 1024 * 1024
RETENTION_STATUS = "GATEWAY_RETENTION_NOT_VERIFIED"
KEY_VARIABLE = "GAPGPT_API_KEY"


def contract_from_dict(value):
    """Explicit provider assumptions. Prices are user-declared, NOT verified bills."""
    if type(value) is not dict or set(value) != {
        "version", "endpoint", "model", "allowed_returned_models", "temperature",
        "n", "max_tokens", "max_input_tokens", "max_calls",
        "max_spend_usd", "input_usd_per_million", "output_usd_per_million",
        "timeout_seconds", "retention_status"}:
        raise ValueError("Exact versioned Gateway contract required")
    if (type(value["version"]) is not str
            or value["version"] not in OUTPUT_CAP_BY_VERSION
            or value["endpoint"] != ENDPOINT
            or type(value["model"]) is not str or not value["model"].strip()
            or type(value["allowed_returned_models"]) is not list
            or not value["allowed_returned_models"]
            or any(type(m) is not str or not m.strip() for m in value["allowed_returned_models"])
            or len(set(value["allowed_returned_models"])) != len(value["allowed_returned_models"])
            or value["model"] not in value["allowed_returned_models"]
            or type(value["temperature"]) not in (float, int) or value["temperature"] != 1
            or type(value["n"]) is not int or value["n"] != 1
            or type(value["max_tokens"]) is not int
            or value["max_tokens"] != OUTPUT_CAP_BY_VERSION[value["version"]]
            or type(value["max_input_tokens"]) is not int
            or not 1 <= value["max_input_tokens"] <= 131072
            or type(value["max_calls"]) is not int or not 1 <= value["max_calls"] <= 74
            or type(value["timeout_seconds"]) is not int or value["timeout_seconds"] != 120
            or value["retention_status"] != RETENTION_STATUS):
        raise ValueError("Gateway parameters differ from approved experimental envelope")
    for key in ("max_spend_usd", "input_usd_per_million", "output_usd_per_million"):
        if type(value[key]) is not str:
            raise ValueError("Decimal amount must be encoded as a string")
        try:
            number = Decimal(value[key])
        except InvalidOperation:
            raise ValueError("Invalid declared price or budget") from None
        if not number.is_finite() or number <= 0:
            raise ValueError("Nonpositive declared price/budget")
    # A local monetary reservation is a guard, not a provider-enforced charge cap.
    # Always reserve worst-case per call, not average tokens observed so far.
    return json.loads(canonical_bytes(value))


def wire_for(payload, config):
    if (payload.get("prompt_version") != RICH_PROMPT_V2
            or payload.get("response_contract") != RICH_VERSION
            or payload.get("phase") not in ("blind", "compare")):
        raise ValueError("Unexpected verifier payload version")
    return canonical_bytes({
        "model": config["model"], "temperature": config["temperature"],
        "n": config["n"], "max_tokens": config["max_tokens"],
        "messages": [{"role": "user", "content": canonical_bytes(payload).decode("utf-8")}]})
        

def worst_call_cost(config):
    return ((Decimal(config["max_input_tokens"]) * Decimal(config["input_usd_per_million"])
             + Decimal(config["max_tokens"]) * Decimal(config["output_usd_per_million"]))
            / Decimal(1000000))


class GatewayResponseError(ValueError):
    """Safe finite incompatibility reason; never contains untrusted response text."""

    CODES = frozenset((
        "HTTP_STATUS_OR_BODY_INVALID",
        "GATEWAY_SECRET_ECHO",
        "RESPONSE_JSON_INVALID",
        "RETURNED_MODEL_MISMATCH",
        "CHOICES_INVALID",
        "TRUNCATED_OR_NONFINAL",
        "ASSISTANT_CONTENT_MISSING",
        "RICH_RESPONSE_JSON_INVALID",
        "PROVIDER_USAGE_MISSING",
        "PROVIDER_USAGE_INVALID",
        "PROVIDER_USAGE_OVER_CAP",
        "PROVIDER_TOTAL_TOKENS_CONFLICT",
        "PROVIDER_RESPONSE_ID_INVALID",
    ))

    def __init__(self, code):
        if code not in self.CODES:
            raise ValueError("Unknown safe gateway diagnostic")
        self.code = code
        super().__init__(code)


def strict_envelope(status, raw, config, key, target_text):
    """Strict complete Chat Completions envelope and source-valid rich L1.

    This reports exact *diagnostic codes*, not a semantic L2 verdict. Never
    include an untrusted response body, API key or provider error text in them.
    """
    if type(status) is not int or status != 200 or type(raw) is not bytes or len(raw) > MAX_BODY:
        raise GatewayResponseError("HTTP_STATUS_OR_BODY_INVALID")
    if key.encode() in raw:
        raise GatewayResponseError("GATEWAY_SECRET_ECHO")
    try:
        envelope = strict_json(raw)
    except (TypeError, ValueError, UnicodeError):
        raise GatewayResponseError("RESPONSE_JSON_INVALID") from None
    if type(envelope) is not dict:
        raise GatewayResponseError("RESPONSE_JSON_INVALID")
    if type(envelope.get("model")) is not str or envelope["model"] not in config["allowed_returned_models"]:
        raise GatewayResponseError("RETURNED_MODEL_MISMATCH")
    choices = envelope.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        raise GatewayResponseError("CHOICES_INVALID")
    if choices[0].get("finish_reason") != "stop":
        raise GatewayResponseError("TRUNCATED_OR_NONFINAL")
    message = choices[0].get("message")
    content = message.get("content") if type(message) is dict else None
    if type(content) is not str or not content.strip():
        raise GatewayResponseError("ASSISTANT_CONTENT_MISSING")
    try:
        value = strict_json(content)
    except (TypeError, ValueError, UnicodeError):
        raise GatewayResponseError("RICH_RESPONSE_JSON_INVALID") from None
    # Real source/exact-quote failures retain the L1_* EvidenceError code.
    validate_rich_result(value, (target_source(target_text),))
    usage = envelope.get("usage")
    if type(usage) is not dict:
        raise GatewayResponseError("PROVIDER_USAGE_MISSING")
    input_tokens, output_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if (type(input_tokens) is not int or type(output_tokens) is not int
            or input_tokens < 0 or output_tokens < 0):
        raise GatewayResponseError("PROVIDER_USAGE_INVALID")
    if input_tokens > config["max_input_tokens"] or output_tokens > config["max_tokens"]:
        raise GatewayResponseError("PROVIDER_USAGE_OVER_CAP")
    total = usage.get("total_tokens")
    if total is not None:
        if type(total) is not int or total != input_tokens + output_tokens:
            raise GatewayResponseError("PROVIDER_TOTAL_TOKENS_CONFLICT")
    response_id = envelope.get("id")
    if response_id is not None and (type(response_id) is not str
                                    or not 1 <= len(response_id) <= 256):
        raise GatewayResponseError("PROVIDER_RESPONSE_ID_INVALID")
    cost = ((Decimal(input_tokens) * Decimal(config["input_usd_per_million"])
             + Decimal(output_tokens) * Decimal(config["output_usd_per_million"]))
            / Decimal(1000000))
    metadata = {"prompt_tokens": input_tokens, "completion_tokens": output_tokens,
                "returned_model": envelope["model"], "estimated_cost_usd": str(cost),
                "cost_status": "DECLARED_RATE_ESTIMATE_NOT_INVOICE"}
    # Optional provider ID never appears in the existing fake response: old
    # completed fake receipts remain byte-for-byte replay-compatible.
    if response_id is not None:
        metadata["provider_response_id"] = response_id
    return value, metadata


class DurableGapGPTVerifier(DurableOfflineFixtureVerifier):
    """Bound live/fake HTTP journal reused by the existing offline pipeline.

    .offline=True is an interface compatibility shim ONLY; orchestrators must
    not call this class without an explicit, separate gateway approval check.
    The runner replaces reported provider usage for any actual live execution.
    """

    offline = True

    def __init__(self, contract, context, audit, *, transport, key, authorized_fake):
        cfg = contract_from_dict(contract)
        if (type(context) is not dict or context.get("version") != VERSION
                or context.get("gateway_contract_sha256") != digest(cfg)
                or type(audit) is not PrivateAudit or type(key) is not str
                or not 12 <= len(key) <= 4096
                or any(ord(c) < 33 or ord(c) > 126 for c in key)
                or type(authorized_fake) is not bool):
            raise ValueError("GapGPT gateway and private context binding required")
        if authorized_fake:
            if not callable(transport):
                raise ValueError("Fake HTTP needs an injected transport")
        elif transport is not None:
            raise ValueError("Actual live mode forbids unapproved transport substitution")
        self.config = cfg
        self.context = json.loads(canonical_bytes(context))
        self.context_digest = digest(context)
        self._journal_version = JOURNAL_VERSION
        self.maximum_calls = cfg["max_calls"]
        self.audit, self.transport, self.key = audit, transport, key
        self.authorized_fake = authorized_fake
        self.path = audit.root / "fixture_journal.sqlite"
        if self.path.is_symlink() or self.path.parent != audit.root:
            raise ValueError("Unsafe gateway journal path")
        self.dispatches = self.hits = 0
        self.halted = False
        self._open_database()
        # Crash/restart with unresolved or rejected phase disables all NEW sends.
        with closing(self._connection()) as db:
            self._verify_binding(db)
            self.halted = bool(db.execute(
                "SELECT count(*) FROM intents WHERE state!='COMPLETED'").fetchone()[0])

    def _budget_accepts_new_intent(self, existing_count):
        if worst_call_cost(self.config) * (existing_count + 1) > Decimal(
                self.config["max_spend_usd"]):
            raise ValueError("Conservative declared budget exhausted")

    def _identity(self, phase, payload, wire, dependency):
        return digest({"version": VERSION, "phase": phase,
                       "context_sha256": self.context_digest,
                       "payload_sha256": digest(payload),
                       "wire_sha256": hashlib.sha256(wire).hexdigest(),
                       "blind_response_sha256": dependency})

    def _validate(self, raw, text):
        return validate_rich_result(raw, (target_source(text),))

    def _completed(self, identity, row, payload, wire, dependency, phase, text):
        expected_payload = digest(payload)
        if row[:3] != (expected_payload, dependency, phase):
            raise ValueError("Historical request identity mismatch")
        if row[3] != "COMPLETED":
            raise EvidenceError("TIMEOUT_UNCERTAIN_NO_RETRY" if row[3] == "UNCERTAIN"
                                else "VERIFIER_FAILURE_UNCERTAIN")
        record = self.audit.read(row[4])
        if (record.get("kind") != "gapgpt_gateway_response"
                or record.get("identity") != identity
                or record.get("context_sha256") != self.context_digest
                or record.get("wire_sha256") != hashlib.sha256(wire).hexdigest()
                or record.get("payload_sha256") != expected_payload
                or record.get("dependency") != dependency):
            raise ValueError("Gateway response receipt binding differs")
        raw = bytes.fromhex(record["raw_hex"])
        if hashlib.sha256(raw).hexdigest() != record["response_sha256"]:
            raise ValueError("Gateway response raw digest mismatch")
        value, meta = strict_envelope(record["http_status"], raw, self.config, self.key, text)
        if meta != record["usage_summary"]:
            raise ValueError("Gateway usage/identity receipt mismatch")
        return json.loads(canonical_bytes(value))

    def _invoke(self, phase, request, payload, dependency=None):
        wire = wire_for(payload, self.config)
        # Treat exact UTF8 wire length as a conservative local input-token proxy,
        # NOT vendor tokenization or billing guarantee.
        if len(wire) > self.config["max_input_tokens"]:
            raise ValueError("Gateway wire exceeds declared conservative input limit")
        identity = self._identity(phase, payload, wire, dependency)
        row = self._get(identity)
        if row is not None:
            result = self._completed(identity, row, payload, wire, dependency, phase, request.text)
            self.hits += 1
            return result
        if self.halted:
            raise EvidenceError("TIMEOUT_UNCERTAIN_NO_RETRY")
        # The call and monetary reservation are checked atomically under BEGIN IMMEDIATE.
        try:
            self._reserve(identity, digest(payload), dependency, phase, request.node_id)
        except ValueError:
            self.halted = True
            raise
        intent = {"kind": "gapgpt_gateway_intent", "identity": identity,
                  "context_sha256": self.context_digest,
                  "payload_sha256": digest(payload),
                  "wire_sha256": hashlib.sha256(wire).hexdigest(),
                  "dependency": dependency, "payload": payload,
                  "wire": json.loads(wire), "provider": "GapGPT",
                  "contract_sha256": digest(self.config)}
        self.audit.read(self.audit.write(intent))
        self.dispatches += 1
        try:
            status, raw = ((self.transport(wire, self.key) if self.authorized_fake else
                            post_once(wire, self.key, target="account-panel-temperature1")))
            if type(raw) is not bytes or len(raw) > MAX_BODY or type(status) is not int:
                raise ValueError("Invalid HTTP transport result")
            # Do not store echoed keys. Retain the response with explicit redaction
            # and rejection rather than exposing any credential in the private audit.
            redacted = raw.replace(self.key.encode(), b"[REDACTED]")
            escaped = json.dumps(self.key)[1:-1].encode("utf-8")
            if escaped:
                redacted = redacted.replace(escaped, b"[REDACTED]")
            response = {"kind": "gapgpt_gateway_response", "identity": identity,
                        "context_sha256": self.context_digest,
                        "payload_sha256": digest(payload),
                        "wire_sha256": hashlib.sha256(wire).hexdigest(),
                        "dependency": dependency, "http_status": status,
                        "raw_hex": redacted.hex(),
                        "response_sha256": hashlib.sha256(redacted).hexdigest()}
            try:
                if redacted != raw:
                    raise ValueError("SECRET_ECHO_REDACTED")
                value, meta = strict_envelope(status, raw, self.config, self.key, request.text)
            except (ValueError, EvidenceError, TypeError, KeyError) as error:
                response["reject_code"] = (
                    error.code if isinstance(error, (EvidenceError, GatewayResponseError))
                    else "INVALID_GATEWAY_ENVELOPE_OR_USAGE")
                receipt = self.audit.write(response)
                self.audit.read(receipt)
                self._settle(identity, "REJECTED", receipt)
                self.halted = True
                if isinstance(error, EvidenceError):
                    raise
                raise EvidenceError("VERIFIER_FAILURE_UNCERTAIN") from None
            response["usage_summary"] = meta
            receipt = self.audit.write(response)
            self.audit.read(receipt)
            self._settle(identity, "COMPLETED", receipt)
            return json.loads(canonical_bytes(value))
        except BaseException:
            self.halted = True
            # If not durably settled, UNCERTAIN persists. Never retry or re-bill.
            raise

    def blind(self, request):
        return self._invoke("blind", request,
                            rich_verifier_input_v2(request.node_id, request.text, request.neighborhood))

    def compare(self, request):
        original = rich_verifier_input_v2(request.node_id, request.text, request.neighborhood)
        original_wire = wire_for(original, self.config)
        old_id = self._identity("blind", original, original_wire, None)
        row = self._get(old_id)
        if row is None:
            raise ValueError("Completed saved Blind prerequisite missing")
        blind = self._completed(old_id, row, original, original_wire, None, "blind", request.text)
        if blind["abstain"] or blind["class_index"] != request.blind_class_index:
            raise ValueError("Gateway Blind prerequisite invalid")
        payload = rich_verifier_input_v2(
            request.node_id, request.text, request.neighborhood,
            candidates=request.historical_candidates, blind_class=request.blind_class_index)
        return self._invoke("compare", request, payload, digest(blind))

    def stats(self):
        with closing(self._connection()) as db:
            self._verify_binding(db)
            records = list(db.execute("SELECT identity,state,receipt FROM intents"))
        usage, spent = {"prompt_tokens": 0, "completion_tokens": 0}, Decimal(0)
        returned_models, rejection_codes = {}, {}
        unknown_billing_attempts = 0
        for _, state, receipt in records:
            if state == "COMPLETED":
                record = self.audit.read(receipt)
                summary = record.get("usage_summary", {})
                if not {"prompt_tokens", "completion_tokens", "estimated_cost_usd",
                        "returned_model"} <= set(summary):
                    raise ValueError("Missing completed provider usage or model")
                usage["prompt_tokens"] += summary["prompt_tokens"]
                usage["completion_tokens"] += summary["completion_tokens"]
                spent += Decimal(summary["estimated_cost_usd"])
                model = summary["returned_model"]
                returned_models[model] = returned_models.get(model, 0) + 1
            else:
                # A rejected or unknown request can still be charged by Gateway.
                # It must never silently disappear from the cost denominator.
                unknown_billing_attempts += 1
                if state == "REJECTED":
                    record = self.audit.read(receipt)
                    if record.get("kind") != "gapgpt_gateway_response":
                        raise ValueError("Invalid rejected Gateway receipt")
                    code = record.get("reject_code", "UNKNOWN_REJECTION")
                    if type(code) is not str or len(code) > 128:
                        raise ValueError("Invalid rejected Gateway diagnostic")
                    rejection_codes[code] = rejection_codes.get(code, 0) + 1
        return {"attempted_calls": len(records), "new_dispatches": self.dispatches,
                "successful_replays": self.hits,
                "state_counts": {s: sum(1 for _, x, _ in records if x == s)
                                 for s in ("COMPLETED", "REJECTED", "UNCERTAIN")},
                "verified_usage": usage, "estimated_cost_usd": str(spent),
                "reserved_cost_upper_usd": str(worst_call_cost(self.config) * len(records)),
                "cost_status": "USER_DECLARED_PRICE_NOT_PROVIDER_BILLING",
                "provider": "GapGPT", "endpoint": self.config["endpoint"],
                "requested_model": self.config["model"],
                "retention_status": RETENTION_STATUS,
                "transport": "FAKE_HTTP" if self.authorized_fake else "LIVE_HTTPS",
                "returned_models": dict(sorted(returned_models.items())),
                "rejection_codes": dict(sorted(rejection_codes.items())),
                "unknown_billing_attempts": unknown_billing_attempts,
                "verified_usage_scope": "COMPLETED_PHASES_ONLY_NOT_ALL_ATTEMPTS"}

