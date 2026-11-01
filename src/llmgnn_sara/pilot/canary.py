"""Owner-operated single GapGPT blind canary. Importing never sends a request."""
import getpass
import hashlib
import http.client
import json
import os
from pathlib import Path
import sqlite3
import ssl
import sys
import warnings
from contextlib import closing
from decimal import Decimal

from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.inputs import canonical_bytes, pair_inputs
from .readiness import ReadinessLedger, CONTRACT_SHA256

HOST = "api.gapapi.com"
ENDPOINT = "https://api.gapapi.com/v1/chat/completions"
IDENTITY = "gapgpt-blind-637-canary-v1"
ROOT = Path(__file__).resolve().parents[3]
MAX_BODY = 1024 * 1024
ACCOUNT_PANEL_IDENTITY = "gapgpt-app-blind-637-canary-v1"


def target_settings(target):
    if target == "historical":
        return HOST, ENDPOINT, IDENTITY, "gapgpt_canary_637"
    if target == "account-panel":
        return ("api.gapgpt.app", "https://api.gapgpt.app/v1/chat/completions",
                ACCOUNT_PANEL_IDENTITY, "gapgpt_app_canary_637")
    raise ValueError("Unapproved target")
SEALS = ("29fa95c7d34f5826b628509e6bad2baced83ac986ebfbc7cadc4bb36d4c31b41",
         "9fd65d82e3cab296afc503813b97b0c0af9e8f4dcb41cd0be1aa20ac34ef1f96")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare():
    base = ROOT / ".local_artifacts/pilot-gapapi"
    seals = []
    for directory, pin in zip((base, base / "pilot"), SEALS):
        manifest = read_pinned_json(directory / "SHA256.json", pin)
        seals.append(manifest)
        for name, digest in manifest["files"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts or ":" in name or "\\" in name:
                raise ValueError("Unsafe seal member")
            read_pinned_json(directory / relative, digest)
    inputs = load_project_inputs(ROOT / ".local_artifacts/frozen", ROOT / ".local_artifacts/authentic")
    pair = next(p for p in inputs.pairs if p.node_id == 637)
    payload = pair_inputs(pair)[0]
    inner = json.loads((base / "pilot/requests/blind-637.json").read_bytes())
    wire_bytes = (base / "gapapi/blind-637.json").read_bytes()
    if sha(wire_bytes) != seals[0]["files"]["gapapi/blind-637.json"]:
        raise ValueError("Wire bytes changed after admission")
    wire = json.loads(wire_bytes)
    expected = {"model": "gpt-6-luna", "temperature": 0.7, "n": 1, "max_tokens": 512,
                "messages": [{"role": "user", "content": canonical_bytes(payload).decode()}]}
    if inner != payload or wire != expected:
        raise ValueError("Sealed canary contract differs")
    # Declared reservation only: this byte check is not vendor tokenization.
    if len(wire_bytes) > 16384:
        raise ValueError("Declared input-byte preflight exceeded; no token guarantee")
    return payload, wire_bytes


def credential():
    key = os.environ.get("GAPGPT_API_KEY")
    if not key:
        if not sys.stdin.isatty():
            raise ValueError("Interactive hidden credential entry required")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("GapGPT API key (hidden): ")
    if not key or not 12 <= len(key) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("Invalid credential format")
    return key


def post_once(wire_bytes, key, *, target="historical"):
    """Fixed TLS host/path, no proxy, redirect, retry, alternate model or endpoint."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()  # Does not enable environment-driven TLS key logging.
    host, _, _, _ = target_settings(target)
    connection = http.client.HTTPSConnection(host, timeout=120, context=context)
    try:
        connection.request("POST", "/v1/chat/completions", body=wire_bytes,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, response.read(MAX_BODY + 1)
    finally:
        connection.close()


def strict_json(raw):
    def unique(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate JSON key")
            result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def redact_decoded(value, key, depth=0):
    if depth > 20:
        raise ValueError("Response nesting exceeded")
    if isinstance(value, dict):
        return {k.replace(key, "[REDACTED]"): redact_decoded(v, key, depth+1) for k,v in value.items()}
    if isinstance(value, list):
        return [redact_decoded(v, key, depth+1) for v in value]
    if isinstance(value, str):
        cleaned = value.replace(key, "[REDACTED]")
        if cleaned.lstrip().startswith(("{", "[")):
            try:
                nested = strict_json(cleaned)
                safe = redact_decoded(nested, key, depth+1)
                if safe != nested:
                    cleaned = json.dumps(safe)
            except (ValueError, TypeError):
                pass
        return cleaned
    return value


def execute(payload, wire, key, audit, ledger, approval, *, transport=None, target="historical"):
    """One attempt. Tests substitute transport; CLI alone gathers owner approval."""
    _, endpoint, identity, _ = target_settings(target)
    expected_payload, expected_wire = prepare()
    if payload != expected_payload or wire != expected_wire:
        raise ValueError("Canary payload differs")
    if type(key) is not str or not 12 <= len(key) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("Invalid credential format")
    if (type(approval) is not dict or any(approval.get(k) is not True for k in ("privacy", "compatibility", "declared_limits"))
            or approval != {"privacy": True, "compatibility": True, "declared_limits": True,
                    "usd_reservation": "0.10", "dispatch": identity}):
        raise ValueError("Explicit scoped approvals required")
    context = {"version": identity, "endpoint": endpoint, "model": "gpt-6-luna",
        "node": 637, "phase": "blind", "wire_sha256": sha(wire), "approval": approval,
        "readiness_contract_sha256": CONTRACT_SHA256, "seal_sha256": list(SEALS),
        "pricing": "OWNER_PROVISIONAL_0.10_INPUT_0.50_OUTPUT_PER_M_NOT_BILLING_CAP"}
    context_sha = sha(canonical_bytes(context))
    with closing(sqlite3.connect(ledger.path)) as db, db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE IF NOT EXISTS canary_context (sha TEXT PRIMARY KEY)")
        rows = db.execute("SELECT sha FROM canary_context").fetchall()
        if rows and rows != [(context_sha,)]:
            raise ValueError("Different execution context")
        if not rows:
            db.execute("INSERT INTO canary_context VALUES (?)", (context_sha,))
    # Full reservation is consumed even on rejection/uncertainty. No release/retry.
    audit.read(audit.write({"kind": "canary_approval", "context": context}))
    ledger.reserve(identity, payload, 16384, 512)
    ledger.mark_dispatched(identity, payload)
    result = {"status": "UNCERTAIN", "l1_status": "NOT_ASSESSED", "usage": None,
              "estimated_cost_usd": None, "cost_status": "UNKNOWN_NOT_VERIFIED_BILLING",
              "accepted_label": None, "l2_status": "NOT_ASSESSED"}
    try:
        status, raw = post_once(wire, key, target=target) if transport is None else transport(wire, key)
        original_sha = sha(raw)
        safe = raw.replace(key.encode(), b"[REDACTED]")
        safe = safe.replace(json.dumps(key)[1:-1].encode(), b"[REDACTED]")
        try:
            decoded = strict_json(safe)
            cleaned = redact_decoded(decoded, key)
            if cleaned != decoded:
                safe = canonical_bytes(cleaned)
        except (ValueError, TypeError):
            pass
        echoed = safe != raw
        raw_receipt = audit.write({"kind": "canary_provider_response", "context_sha256": context_sha,
            "http_status": status, "raw_hex": safe.hex(), "original_response_sha256": original_sha,
            "persisted_response_sha256": sha(safe), "secret_echo_redacted": echoed,
            "body_complete": len(raw) <= MAX_BODY})
        audit.read(raw_receipt)
        reason, inner_bytes = "INVALID_ENVELOPE", safe
        parsed = None
        if len(raw) > MAX_BODY:
            reason = "BODY_LIMIT"
        elif echoed:
            reason = "SECRET_ECHO_REDACTED"
        elif not 200 <= status < 300:
            reason = "HTTP_REJECTION_NO_RETRY"
        else:
            try:
                envelope = strict_json(safe)
                if envelope.get("model") not in (None, "gpt-6-luna"):
                    raise ValueError("Unapproved returned model identifier")
                usage = envelope.get("usage")
                result["usage"] = usage
                if isinstance(usage, dict):
                    i, o = usage.get("prompt_tokens"), usage.get("completion_tokens")
                    if any(v is not None and (type(v) is not int or v < 0) for v in (i,o)):
                        raise ValueError("Invalid usage")
                    if type(i) is int and type(o) is int and i >= 0 and o >= 0:
                        result["estimated_cost_usd"] = str((Decimal(i)*Decimal('.10') + Decimal(o)*Decimal('.50'))/Decimal(1000000))
                        result["cost_status"] = "PROVISIONAL_RATE_ESTIMATE_NOT_INVOICE"
                        if i > 16384 or o > 512:
                            raise ValueError("Usage exceeded declared reservation")
                choices = envelope["choices"]
                if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
                    reason = "TRUNCATED_OR_NONFINAL"
                else:
                    content = choices[0]["message"]["content"]
                    if type(content) is not str:
                        raise ValueError("Nontext response")
                    strict_json(content)
                    inner_bytes, reason = content.encode(), "PARSER_L1"
            except (ValueError, KeyError, TypeError, AttributeError):
                reason = "INVALID_ENVELOPE_OR_USAGE"
        settled = ledger.settle(identity, payload, inner_bytes, audit,
                               rejection_reason=None if reason == "PARSER_L1" else reason)
        result.update(status=settled["state"], l1_status="PASS" if reason == "PARSER_L1" and settled["state"] == "COMPLETED" else "FAIL",
                      reason=settled["reason"] if reason == "PARSER_L1" else reason,
                      provider_response_receipt=raw_receipt)
    except BaseException:
        # Never stringify exceptions: server/HTTP errors could contain credentials.
        result["reason"] = "UNKNOWN_EXECUTION_OR_AUDIT_FAILURE_NO_RETRY"
    try:
        receipt = audit.write({"kind": "canary_result", "context_sha256": context_sha, "result": result})
        audit.read(receipt)
        return {**result, "result_receipt": receipt}
    except BaseException:
        return {"status": "UNCERTAIN", "reason": "AUDIT_UNAVAILABLE_NO_RETRY", "accepted_label": None}


def main(*, target="historical"):
    try:
        if len(sys.argv) != 1 or not sys.stdin.isatty():
            raise ValueError("Run interactively without arguments")
        _, endpoint, identity, directory = target_settings(target)
        payload, wire = prepare()
        audit = PrivateAudit(ROOT / ".local_artifacts" / directory)
        ledger = ReadinessLedger(audit.root / "intent.sqlite")
        if ledger.snapshot():
            raise ValueError("Existing canary intent; no repeat or automatic recovery")
        print("GapGPT | " + endpoint + " | gpt-6-luna | node637 | BLIND ONLY")
        print("One attempt; input reservation16384/output512. Provisional estimate USD0.0018944.")
        print("USD0.10 reservation is NOT a provider billing guarantee. No comparison/retry.")
        approval = {}
        for field, phrase in (("privacy", "APPROVE PRIVACY"), ("compatibility", "APPROVE SEALED WIRE"),
                              ("declared_limits", "APPROVE DECLARED LIMITS")):
            approval[field] = input("Type " + phrase + ": ") == phrase
        approval["usd_reservation"] = input("Confirm full USD reservation by typing 0.10: ")
        if not all(approval.get(k) is True for k in ("privacy", "compatibility", "declared_limits")) or approval["usd_reservation"] != "0.10":
            raise ValueError("Approvals incomplete")
        key = credential()
        approval["dispatch"] = input("Authorize exactly one request; type " + identity + ": ")
        result = execute(payload, wire, key, audit, ledger, approval, target=target)
        # Raw text, labels, response bodies, identifiers and usage stay private.
        print(json.dumps({k: result.get(k) for k in ("status", "l1_status", "cost_status", "reason")}))
        print("Private results: .local_artifacts/" + directory + "; do not rerun after any intent.")
        return 0 if result["status"] == "COMPLETED" else 1
    except BaseException:
        print("Canary blocked or interrupted; inspect private state. No automatic retry.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
