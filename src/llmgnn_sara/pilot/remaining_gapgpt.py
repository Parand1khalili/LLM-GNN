"""Owner-operated continuation of the sealed pilot. No import-time execution."""
from contextlib import closing
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import sys

from . import canary
from .protocol import materialize_comparison
from .readiness import ReadinessLedger, encoded
from ..io.frozen import read_pinned_json
from ..sara3.audit import PrivateAudit
from ..sara3.evidence import validate_result
from ..sara3.inputs import canonical_bytes

VERSION = "gapgpt-six-node-remaining-t1-v1"
NODES = (1243, 130, 682, 2396, 653)
ENDPOINT = "https://api.gapgpt.app/v1/chat/completions"
MODEL = "gpt-6-luna"
REVISION = "gpt-6-luna-2026-09-22"
ROOT = canary.ROOT
DIRECTORY = "gapgpt_remaining_pilot_v1"
CONTRACT = {"version": VERSION, "provider": "GapGPT", "endpoint": ENDPOINT,
    "requested_model": MODEL, "allowed_returned_models": [MODEL, REVISION],
    "identity_provenance": "OWNER_APPROVED_EXACT_MAPPING_FROM_OBSERVED_RESPONSE_NOT_UPSTREAM_PROOF",
    "order": list(NODES), "excluded_prior_node": 637, "temperature": 1, "n": 1,
    "max_tokens": 512, "reasoning_effort": "OMITTED", "maximum_calls": 10,
    "declared_input_per_call": 16384, "declared_output_per_call": 512,
    "aggregate_local_reservation_usd": "0.10", "pricing_status": "OWNER_PROVISIONAL_NOT_BILLING_CAP",
    "seals": list(canary.SEALS), "resume": "FORBIDDEN_AFTER_START", "retries": 0,
    "l2_status": "NOT_ASSESSED", "accepted_label": None}


def identity_allowed(provider, endpoint, requested, returned):
    return (provider == "GapGPT" and endpoint == ENDPOINT and requested == MODEL
            and type(returned) is str and returned in (MODEL, REVISION))


def _read_receipts(directory):
    """Read content-addressed receipts without changing historical ACLs or state."""
    records = {}
    for path in directory.glob("*.json"):
        raw = path.read_bytes()
        if path.is_symlink() or canary.sha(raw) != path.stem:
            raise ValueError("Historical receipt integrity failure")
        records[path.stem] = canary.strict_json(raw)
    return records


def prior_637(root):
    directory = root / ".local_artifacts/gapgpt_app_t1_canary_637"
    records = _read_receipts(directory)
    receipt, record = next((k, v) for k, v in records.items()
                           if v.get("kind") == "canary_provider_response")
    raw = bytes.fromhex(record["raw_hex"])
    if (record["http_status"] != 200 or not record["body_complete"]
            or record["secret_echo_redacted"]
            or record["original_response_sha256"] != canary.sha(raw)
            or record["persisted_response_sha256"] != canary.sha(raw)):
        raise ValueError("Prior response cannot be admitted")
    envelope = canary.strict_json(raw)
    if envelope["model"] != REVISION or envelope["choices"][0]["finish_reason"] != "stop":
        raise ValueError("Unexpected prior response")
    value = canary.strict_json(envelope["choices"][0]["message"]["content"])
    result = validate_result(value, "")  # Abstention requires no paper text.
    if not result["abstain"]:
        raise ValueError("Prior abstention required")
    approval = next(v for v in records.values() if v.get("kind") == "canary_approval")
    _, prior_wire = canary.prepare(target="account-panel-temperature1")
    context_sha = canary.sha(canonical_bytes(approval["context"]))
    if (approval["context"]["wire_sha256"] != canary.sha(prior_wire)
            or record["context_sha256"] != context_sha):
        raise ValueError("Prior response context differs")
    with closing(sqlite3.connect((directory / "intent.sqlite").resolve().as_uri()+"?mode=ro", uri=True)) as db:
        entries = db.execute("SELECT id,request_sha,state,raw_sha,audit_sha FROM intents").fetchall()
    if len(entries) != 1 or entries[0][0] != canary.TEMPERATURE1_IDENTITY or entries[0][2] != "REJECTED":
        raise ValueError("Prior terminal ledger differs")
    prior_payload, _ = canary.prepare(target="account-panel-temperature1")
    readiness = records[entries[0][4]]
    if (entries[0][1] != canary.sha(encoded(prior_payload))
            or readiness["request_sha256"] != entries[0][1]
            or readiness["raw_sha256"] != entries[0][3]
            or canary.sha(bytes.fromhex(readiness["raw_hex"])) != entries[0][3]):
        raise ValueError("Prior ledger/audit binding differs")
    return {"node": 637, "blind": {"state": "HISTORICAL_REJECTED_DIAGNOSTIC_ONLY",
        "original_ledger_state": "REJECTED", "estimated_cost_usd": "0.0001514",
        "actual_cost_usd": None, "billing_status": "UNKNOWN_NOT_VERIFIED_BILLING",
        "http_status": 200, "parse_status": "PASS", "l1_status": "PASS",
        "abstain": True, "class_index": None, "usage": envelope.get("usage"),
        "provider_model": envelope["model"], "provider_receipt": receipt,
        "review_eligibility": "ABSTENTION_ONLY_NO_CLASS_EVIDENCE"},
        "compare": {"state": "NOT_PERMITTED_BLIND_ABSTENTION"}}


def verify_no_prior_dispatch(root, payloads, *, reserved_prefix=VERSION):
    expected = {canary.sha(encoded(p)) for p in payloads}
    # Only operational pilot stores; never inspect human-review or development intake.
    directories = [p for p in (root / ".local_artifacts").iterdir()
                   if p.is_dir() and (p.name.startswith("gapgpt") or p.name.startswith("pilot"))]
    for directory in directories:
        for path in list(directory.rglob("*.sqlite")) + list(directory.rglob("*.db")):
            if path.is_symlink():
                raise ValueError("Symlink ledger rejected")
            with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True)) as db:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "intents" not in tables:
                    continue
                columns = {r[1] for r in db.execute("PRAGMA table_info(intents)")}
                if not {"id", "request_sha", "state"} <= columns:
                    raise ValueError("Unrecognized operational ledger; review required")
                for identity, digest, state in db.execute("SELECT id,request_sha,state FROM intents"):
                    if digest in expected or identity.startswith(reserved_prefix):
                        raise ValueError("Existing intent; no continuation/retry allowed")


def sealed_inputs(root=ROOT):
    canary.prepare(target="account-panel-temperature1")  # All sealed members + authentic inputs.
    manifest = json.loads((root / "manifests/recovered_sources.json").read_bytes())
    for entry in manifest["files"]:
        path = Path(entry["local_path"])
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "recovered_sources":
            raise ValueError("Invalid recovered source path")
        if canary.sha((root / path).read_bytes()) != entry["sha256"]:
            raise ValueError("Recovered source hash conflict")
    base = root / ".local_artifacts/pilot-gapapi"
    seal = read_pinned_json(base / "SHA256.json", canary.SEALS[0])
    inner_seal = read_pinned_json(base / "pilot/SHA256.json", canary.SEALS[1])
    protocol = json.loads((base / "pilot/pilot_protocol.json").read_bytes())
    if protocol["selection"]["selected_node_ids"] != [637, *NODES]:
        raise ValueError("Pilot order differs")
    requests = {}
    for node in NODES:
        blind = read_pinned_json(base / f"pilot/requests/blind-{node}.json",
                                inner_seal["files"][f"requests/blind-{node}.json"])
        comparison = read_pinned_json(base / f"pilot/templates/compare-{node}.json",
                                inner_seal["files"][f"templates/compare-{node}.json"])
        old_wire = read_pinned_json(base / f"gapapi/blind-{node}.json",
                                   seal["files"][f"gapapi/blind-{node}.json"])
        if (old_wire != {"model": MODEL, "temperature": .7, "n": 1, "max_tokens": 512,
                        "messages": [{"role": "user", "content": canonical_bytes(blind).decode()}]}):
            raise ValueError("Unexpected sealed wire")
        requests[node] = (blind, comparison)
    previous = prior_637(root)
    return requests, previous


def prepare(root=ROOT):
    requests, previous = sealed_inputs(root)
    verify_no_prior_dispatch(root, [p[0] for p in requests.values()])
    return requests, previous


def wire_for(payload):
    wire = canonical_bytes({"model": MODEL, "temperature": 1, "n": 1, "max_tokens": 512,
                           "messages": [{"role": "user", "content": canonical_bytes(payload).decode()}]})
    if len(wire) > 16384:
        raise ValueError("Declared input byte preflight exceeded; not provider tokenization")
    return wire


def start(ledger, audit, approval, requests):
    if tuple(requests) != NODES:
        raise ValueError("Wrong remaining node order/membership")
    expected = {"privacy": True, "sealed_wire": True, "declared_limits": True,
                "exact_revision": True, "reservation_usd": "0.10", "dispatch": VERSION}
    if type(approval) is not dict or approval != expected or any(
            approval[k] is not True for k in ("privacy", "sealed_wire", "declared_limits", "exact_revision")):
        raise ValueError("Fresh batch approvals incomplete")
    for blind, template in requests.values():
        wire_for(blind)
        for label in range(7):
            wire_for(materialize_comparison(template, label))
    binding = {"contract": CONTRACT, "approval": approval,
               "recovered_source_manifest_sha256": canary.sha((ROOT / "manifests/recovered_sources.json").read_bytes()),
               "request_pins": {str(node): [canary.sha(canonical_bytes(p)) for p in pair]
                                for node, pair in requests.items()}}
    receipt = audit.write({"kind": "remaining_batch_approval", "binding": binding})
    audit.read(receipt)
    digest = canary.sha(canonical_bytes(binding))
    with closing(sqlite3.connect(ledger.path)) as db, db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT count(*) FROM intents").fetchone()[0]:
            raise ValueError("Existing batch intent; restart forbidden")
        db.execute("CREATE TABLE IF NOT EXISTS remaining_run (id INTEGER PRIMARY KEY CHECK(id=1), digest TEXT, state TEXT, binding BLOB)")
        if db.execute("SELECT count(*) FROM remaining_run").fetchone()[0]:
            raise ValueError("Batch previously started; review required, no resume")
        db.execute("INSERT INTO remaining_run VALUES (1,?, 'RUNNING',?)", (digest, canonical_bytes(binding)))
    return digest


def dispatch(node, phase, payload, key, ledger, audit, digest, *, dependency=None, transport=None):
    if (node not in NODES or phase not in ("blind", "compare") or payload.get("node_id") != node
            or payload.get("phase") != phase):
        raise ValueError("Request scope mismatch")
    if type(key) is not str or not 12 <= len(key) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("Invalid credential format")
    identity = f"{VERSION}:{node}:{phase}"
    wire = wire_for(payload)
    with closing(sqlite3.connect(ledger.path)) as db:
        bound = db.execute("SELECT digest,state,binding FROM remaining_run WHERE id=1").fetchone()
        if not bound or bound[:2] != (digest, "RUNNING") or canary.sha(bound[2]) != digest:
            raise ValueError("Wrong batch binding/state")
        binding = canary.strict_json(bound[2])
        if binding["contract"] != CONTRACT:
            raise ValueError("Contract changed")
        previous = db.execute("SELECT id,state,audit_sha FROM intents ORDER BY rowid").fetchall()
        count, inputs, outputs = db.execute("SELECT count(*),coalesce(sum(input_cap),0),coalesce(sum(output_cap),0) FROM intents").fetchone()
        if count >= 10 or inputs+16384 > 163840 or outputs+512 > 5120:
            raise ValueError("Batch reservation exhausted")
    template = json.loads(canonical_bytes(payload))
    if phase == "compare":
        blind_id = f"{VERSION}:{node}:blind"
        if not previous or previous[-1][:2] != (blind_id, "COMPLETED") or type(dependency) is not dict:
            raise ValueError("Comparison requires completed blind")
        prior = audit.read(previous[-1][2])
        value = canary.strict_json(bytes.fromhex(prior["raw_hex"]))
        validated = validate_result(value, payload["target"]["text"])
        if validated["abstain"] or payload["blind_class_index"] != validated["class_index"]:
            raise ValueError("Comparison forbidden or wrong binding")
        provider_record = audit.read(dependency["blind_provider_receipt"])
        provider_value = canary.strict_json(canary.strict_json(bytes.fromhex(provider_record["raw_hex"]))["choices"][0]["message"]["content"])
        if provider_value != value or dependency["blind_response_sha256"] != canary.sha(canonical_bytes(value)):
            raise ValueError("Blind response dependency differs")
        template["blind_class_index"] = "$BLIND_CLASS_INDEX"
        if dependency["template_sha256"] != canary.sha(canonical_bytes(template)):
            raise ValueError("Comparison template differs")
    elif previous:
        prior_node = int(previous[-1][0].split(":")[-2])
        if previous[-1][1] != "COMPLETED" or NODES.index(node) != NODES.index(prior_node)+1:
            raise ValueError("Wrong sequence or previous failure")
        if previous[-1][0].endswith(":blind"):
            prior = audit.read(previous[-1][2])
            value = canary.strict_json(bytes.fromhex(prior["raw_hex"]))
            if not value["abstain"]:
                raise ValueError("Previous comparison still required")
    elif node != NODES[0]:
        raise ValueError("Wrong first node")
    pin = binding["request_pins"][str(node)][phase == "compare"]
    if canary.sha(canonical_bytes(template)) != pin:
        raise ValueError("Payload differs from admitted request")
    context = {"kind": "remaining_request", "batch_digest": digest, "identity": identity,
               "payload_sha256": canary.sha(encoded(payload)), "wire_sha256": canary.sha(wire),
               "dependency": dependency, "identity_policy": CONTRACT["identity_provenance"]}
    context_receipt = audit.write(context)
    audit.read(context_receipt)
    ledger.reserve(identity, payload, 16384, 512)
    ledger.mark_dispatched(identity, payload)
    result = canary._dispatch_recorded(payload, wire, key, audit, ledger, identity,
        canary.sha(canonical_bytes(context)), transport=transport, target="account-panel-temperature1",
        model_check=lambda returned: identity_allowed("GapGPT", ENDPOINT, MODEL, returned))
    return phase_outcome(result, audit, payload)


def phase_outcome(result, audit, payload):
    outcome = {"state": result["status"], "reason": result.get("reason"),
        "l1_status": result.get("l1_status"), "parse_status": "NOT_VERIFIED",
        "accepted_label": None, "l2_status": "NOT_ASSESSED", "result_receipt": result.get("result_receipt"),
        "estimated_cost_usd": result.get("estimated_cost_usd"), "usage": result.get("usage"),
        "actual_cost_usd": None, "billing_status": "UNKNOWN_NOT_VERIFIED_BILLING"}
    if result.get("provider_response_receipt"):
        record = audit.read(result["provider_response_receipt"])
        outcome.update(http_status=record["http_status"], provider_receipt=result["provider_response_receipt"])
        try:
            envelope = canary.strict_json(bytes.fromhex(record["raw_hex"]))
            outcome["provider_model"] = envelope.get("model")
            outcome["finish_reason"] = envelope["choices"][0].get("finish_reason")
            usage = envelope.get("usage")
            details = usage.get("completion_tokens_details") if type(usage) is dict else None
            outcome["reasoning_tokens"] = details.get("reasoning_tokens") if type(details) is dict else None
            value = canary.strict_json(envelope["choices"][0]["message"]["content"])
            outcome["parse_status"] = "PASS"
        except (ValueError, KeyError, TypeError):
            outcome["parse_status"] = "FAIL_OR_UNAVAILABLE"
        if result["status"] == "COMPLETED":
            envelope = canary.strict_json(bytes.fromhex(record["raw_hex"]))
            value = canary.strict_json(envelope["choices"][0]["message"]["content"])
            validated = validate_result(value, payload["target"]["text"])
            outcome.update(parse_status="PASS", provider_model=envelope["model"],
                class_index=validated["class_index"], abstain=validated["abstain"],
                evidence_count=len(validated["evidence"]), response_sha256=canary.sha(canonical_bytes(value)),
                review_eligibility="ABSTENTION_ONLY_NO_CLASS_EVIDENCE" if validated["abstain"] else "L1_EVIDENCE_AVAILABLE_L2_NOT_ASSESSED")
    return outcome


def run(requests, previous, key, ledger, audit, digest, *, transport=None):
    with closing(sqlite3.connect(ledger.path)) as db:
        if (db.execute("SELECT digest,state FROM remaining_run WHERE id=1").fetchone() != (digest, "RUNNING")
                or db.execute("SELECT count(*) FROM intents").fetchone()[0]):
            raise ValueError("Existing execution state; automatic run/recovery forbidden")
    rows = [previous] + [{"node": n, "blind": {"state": "NOT_ATTEMPTED"},
                         "compare": {"state": "NOT_ATTEMPTED"}} for n in NODES]
    summary = {"version": VERSION, "batch_digest": digest, "rows": rows,
               "accepted_label": None, "l2_status": "NOT_ASSESSED"}
    try:
        for row in rows[1:]:
            node = row["node"]
            blind, template = requests[node]
            row["blind"] = dispatch(node, "blind", blind, key, ledger, audit, digest, transport=transport)
            audit.read(audit.write({"kind": "remaining_progress", "summary": summary}))
            if row["blind"]["state"] != "COMPLETED":
                raise ValueError("Blind failed; halt")
            if row["blind"]["abstain"]:
                row["compare"] = {"state": "NOT_PERMITTED_BLIND_ABSTENTION"}
                continue
            comparison = materialize_comparison(template, row["blind"]["class_index"])
            dependency = {"blind_provider_receipt": row["blind"]["provider_receipt"],
                          "blind_response_sha256": row["blind"]["response_sha256"],
                          "template_sha256": canary.sha(canonical_bytes(template))}
            row["compare"] = dispatch(node, "compare", comparison, key, ledger, audit, digest,
                                       dependency=dependency, transport=transport)
            audit.read(audit.write({"kind": "remaining_progress", "summary": summary}))
            if row["compare"]["state"] != "COMPLETED":
                raise ValueError("Comparison failed; halt")
        state = "FINISHED"
    except BaseException:
        state = "HALTED_REVIEW_REQUIRED_NO_RETRY"
    return finish_summary(summary, ledger, audit, digest, state)


def finish_summary(summary, ledger, audit, digest, state):
    rows = summary["rows"]
    snapshot = ledger.snapshot()
    for entry in snapshot:
        node, phase = int(entry[0].split(":")[-2]), entry[0].split(":")[-1]
        row = next(r for r in rows if r["node"] == node)
        if row[phase]["state"] == "NOT_ATTEMPTED":
            row[phase] = {"state": entry[3], "reason": "LOCAL_FAILURE_REVIEW_REQUIRED_NO_RETRY",
                          "parse_status": "UNAVAILABLE", "l1_status": "NOT_ASSESSED"}
    outcomes = [r[p] for r in rows if r["node"] != 637 for p in ("blind", "compare")
                if not r[p].get("historical", False)]
    usages = [o["usage"] for o in outcomes if type(o.get("usage")) is dict]
    totals = {k: sum(u[k] for u in usages if type(u.get(k)) is int and u[k] >= 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    totals["reasoning_tokens"] = sum(u.get("completion_tokens_details", {}).get("reasoning_tokens", 0) for u in usages
                                   if type(u.get("completion_tokens_details", {})) is dict
                                   and type(u.get("completion_tokens_details", {}).get("reasoning_tokens", 0)) is int
                                   and u.get("completion_tokens_details", {}).get("reasoning_tokens", 0) >= 0)
    estimates = [Decimal(o["estimated_cost_usd"]) for o in outcomes if o.get("estimated_cost_usd") is not None]
    attempted = sum(r[3] != "PENDING" for r in snapshot)
    summary.update(state=state, dispatch_attempts_upper_bound=sum(r[3] != "PENDING" for r in snapshot),
                   historical_637_included_in_new_totals=False,
                   confirmed_http_responses=sum("http_status" in o for o in outcomes),
                   reported_usage_totals=totals, usage_records=len(usages),
                   reasoning_usage_records=sum(type(o.get("reasoning_tokens")) is int for o in outcomes),
                   usage_missing_count=sum(r[3] != "PENDING" for r in snapshot)-len(usages),
                   estimated_cost_usd=str(sum(estimates, Decimal(0))) if len(estimates) == attempted else None,
                   known_estimate_subtotal_usd=str(sum(estimates, Decimal(0))),
                   estimate_missing_count=attempted-len(estimates),
                   actual_cost_usd=None, billing_status="UNKNOWN_NOT_VERIFIED_BILLING",
                   not_attempted_phases=sum(o["state"] == "NOT_ATTEMPTED" for o in outcomes),
                   state_counts={s: sum(r[3] == s for r in snapshot) for s in ("PENDING", "UNCERTAIN", "COMPLETED", "REJECTED")})
    receipt = audit.write({"kind": "remaining_summary", "summary": summary})
    audit.read(receipt)
    with closing(sqlite3.connect(ledger.path)) as db, db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("UPDATE remaining_run SET state=? WHERE id=1 AND digest=?", (state, digest))
    return summary, receipt


def main():
    try:
        if len(sys.argv) != 1 or not sys.stdin.isatty():
            raise ValueError("Interactive local approvals required")
        requests, previous = prepare()
        audit = PrivateAudit(ROOT / ".local_artifacts" / DIRECTORY)
        ledger = ReadinessLedger(audit.root / "intent.sqlite")
        with closing(sqlite3.connect(ledger.path)) as db:
            if db.execute("SELECT count(*) FROM sqlite_master WHERE name='remaining_run'").fetchone()[0]:
                raise ValueError("Batch already started; no resume")
        print(f"GapGPT | {ENDPOINT} | {MODEL} -> exact {REVISION} (provider-reported)")
        print("Order1243,130,682,2396,653; node637 excluded permanently; max10 calls; no retry/resume.")
        print("temperature1/n1/max_tokens512; reasoning_effort omitted; sealed messages unchanged.")
        print("Aggregate declared input163840/output5120; byte preflight is not tokenization.")
        print("Provisional maximum estimate USD0.018944 at owner rates; NOT verified billing/cap.")
        print("Fresh aggregate USD0.10 reservation required; prior canary approvals do not apply.")
        approval = {}
        for field, phrase in (("privacy", "APPROVE BATCH PRIVACY"), ("sealed_wire", "APPROVE TEMPERATURE 1 SEALED WIRE"),
                              ("declared_limits", "APPROVE 10 CALL DECLARED LIMITS"), ("exact_revision", "APPROVE EXACT OBSERVED REVISION")):
            approval[field] = input("Type " + phrase + ": ") == phrase
            if approval[field] is not True:
                raise ValueError("Approval declined")
        approval["reservation_usd"] = input("Confirm fresh aggregate USD reservation; type 0.10: ")
        if approval["reservation_usd"] != "0.10":
            raise ValueError("Budget declined")
        key = canary.credential()
        approval["dispatch"] = input("Authorize remaining batch; type " + VERSION + ": ")
        # Recheck prior dispatch and seals after owner interaction, before persisting start.
        verified, prior = prepare()
        if verified != requests or prior != previous:
            raise ValueError("Inputs changed")
        digest = start(ledger, audit, approval, requests)
        summary, _ = run(requests, previous, key, ledger, audit, digest)
        print(json.dumps({"state": summary["state"], "dispatch_attempts_upper_bound": summary["dispatch_attempts_upper_bound"],
                          "state_counts": summary["state_counts"]}))
        print("Private summary: .local_artifacts/" + DIRECTORY + "; never rerun after start.")
        return 0 if summary["state"] == "FINISHED" else 1
    except BaseException:
        print("Batch blocked/interrupted. No automatic retry or resume; inspect private ledger.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
