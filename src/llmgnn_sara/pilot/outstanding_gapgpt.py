"""Explicit post-observation continuation; never redispatch a preserved blind."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

from . import canary, remaining_gapgpt as prior
from . import identity as identity_policy
from .protocol import materialize_comparison
from .readiness import ReadinessLedger, encoded
from ..sara3.audit import PrivateAudit
from ..sara3.evidence import QUOTE_MATCH_VERSION, validate_result
from ..sara3.inputs import canonical_bytes

VERSION = "gapgpt-outstanding-l1-wrapper-v1"
DIRECTORY = "gapgpt_outstanding_l1_v1"
FOUR_VERSION = "gapgpt-four-unattempted-v1"
FOUR_DIRECTORY = "gapgpt_four_unattempted_v1"
ALIAS_VERSION = "gapgpt-post130-exact-identities-v1"
ALIAS_DIRECTORY = "gapgpt_post130_v1"
BLIND_VERSION = "gapgpt-three-blind-only-v1"
BLIND_DIRECTORY = "gapgpt_three_blind_only_v1"
NODES = (130, 682, 2396, 653)
RULE = "sara.l1.decorative_quote_match.v1"
ROOT = canary.ROOT


def _one(records, field, value):
    matches = [(k, v) for k, v in records.items() if v.get(field) == value]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous provenance record")
    return matches[0]


def preserved_1243(root, blind):
    directory = root / ".local_artifacts/gapgpt_remaining_pilot_v1"
    records = prior._read_receipts(directory)
    provider_id, provider = _one(records, "kind", "canary_provider_response")
    context_id, context = _one(records, "kind", "remaining_request")
    approval_id, approval = _one(records, "kind", "remaining_batch_approval")
    raw = bytes.fromhex(provider["raw_hex"])
    if (provider["http_status"] != 200 or not provider["body_complete"] or provider["secret_echo_redacted"]
            or canary.sha(raw) != provider["original_response_sha256"]
            or canary.sha(raw) != provider["persisted_response_sha256"]
            or provider["context_sha256"] != canary.sha(canonical_bytes(context))):
        raise ValueError("Preserved provider/context hash mismatch")
    with closing(sqlite3.connect((directory / "intent.sqlite").resolve().as_uri()+"?mode=ro", uri=True)) as db:
        entries = db.execute("SELECT id,request_sha,state,raw_sha,audit_sha FROM intents").fetchall()
        run = db.execute("SELECT digest,state,binding FROM remaining_run").fetchone()
    if (len(entries) != 1 or entries[0][0] != prior.VERSION+":1243:blind" or entries[0][2] != "REJECTED"
            or run[1] != "HALTED_REVIEW_REQUIRED_NO_RETRY" or canary.sha(run[2]) != run[0]
            or canary.strict_json(run[2]) != approval["binding"]
            or context["batch_digest"] != run[0] or context["identity"] != entries[0][0]):
        raise ValueError("Original terminal state/binding differs; no recovery dispatch")
    entry = entries[0]
    if (entry[1] != canary.sha(encoded(blind)) or context["payload_sha256"] != entry[1]
            or context["wire_sha256"] != canary.sha(prior.wire_for(blind))):
        raise ValueError("Preserved request differs from sealed blind")
    envelope = canary.strict_json(raw)
    if (envelope["model"] != prior.REVISION or len(envelope["choices"]) != 1
            or envelope["choices"][0]["finish_reason"] != "stop"):
        raise ValueError("Preserved identity/envelope invalid")
    content = envelope["choices"][0]["message"]["content"]
    value = canary.strict_json(content)
    readiness = records[entry[4]]
    if (readiness["request_sha256"] != entry[1] or readiness["reason"] != "L1_QUOTE_NOT_FOUND"
            or readiness["raw_sha256"] != entry[3] or canary.sha(content.encode()) != entry[3]
            or bytes.fromhex(readiness["raw_hex"]) != content.encode()):
        raise ValueError("Original rejection receipt differs")
    result = validate_result(value, blind["target"]["text"])
    diagnostic_id, diagnostic = _one(prior._read_receipts(root / ".local_artifacts/gapgpt_1243_l1_reassessment"),
                                    "schema", "sara.l1.diagnostic_reassessment.v1")
    if (QUOTE_MATCH_VERSION != RULE or diagnostic["rule_version"] != RULE
            or diagnostic["rule_source_sha256"] != canary.sha((root / "src/llmgnn_sara/sara3/evidence.py").read_bytes())
            or diagnostic["provider_response_receipt"] != provider_id
            or diagnostic["original_request_receipt"] != context_id
            or diagnostic["original_readiness_receipt"] != entry[4]
            or diagnostic["original_response_sha256"] != canary.sha(raw)
            or diagnostic["inner_response_sha256"] != entry[3]
            or diagnostic["request_sha256"] != entry[1]
            or diagnostic["wire_sha256"] != context["wire_sha256"]
            or diagnostic["batch_digest"] != run[0]
            or diagnostic["node_id"] != 1243 or diagnostic["phase"] != "blind"
            or diagnostic["original_outcome"]["ledger_state"] != "REJECTED"
            or diagnostic["original_outcome"]["l1_status"] != "FAIL"
            or diagnostic["original_outcome"]["reason"] != "L1_QUOTE_NOT_FOUND"
            or diagnostic["diagnostic_outcome"]["l1_status"] != "PASS"
            or diagnostic["diagnostic_outcome"]["abstain"] != result["abstain"]
            or diagnostic["diagnostic_outcome"]["source_exact_under_revised_rule"] is not True
            or diagnostic["diagnostic_outcome"]["original_acceptance_upgraded"] is not False
            or diagnostic["diagnostic_outcome"]["accepted_label"] is not None):
        raise ValueError("Reassessment provenance/version mismatch")
    lineage = {"provider_receipt": provider_id, "request_receipt": context_id,
               "original_readiness_receipt": entry[4], "approval_receipt": approval_id,
               "diagnostic_receipt": diagnostic_id, "original_raw_sha256": canary.sha(raw),
               "inner_response_sha256": entry[3], "canonical_response_sha256": canary.sha(canonical_bytes(value)),
               "request_sha256": entry[1], "wire_sha256": context["wire_sha256"],
               "original_ledger_state": "REJECTED", "rule_version": RULE}
    outcome = {"state": "HISTORICAL_REJECTED_DIAGNOSTIC_L1_PASS", "historical": True,
               "original_l1_status": "FAIL", "original_ledger_state": "REJECTED",
               "l1_status": "PASS", "abstain": result["abstain"], "class_index": result["class_index"],
               "http_status": 200, "parse_status": "PASS", "usage": envelope.get("usage"),
               "provider_model": envelope["model"], "lineage": lineage,
               "accepted_label": None, "l2_status": "NOT_ASSESSED"}
    return outcome


def rejected_comparison(root, payload, lineage, *, node=1243):
    """Admit the previous genuine failure as history, never as a new intent."""
    directory = root / ".local_artifacts" / (ALIAS_DIRECTORY if node == 130 else DIRECTORY)
    version = ALIAS_VERSION if node == 130 else VERSION
    records = prior._read_receipts(directory)
    provider_id, provider = _one(records, "kind", "canary_provider_response")
    context_id, context = _one(records, "kind", "outstanding_request")
    _, approval = _one(records, "kind", "outstanding_approval")
    with closing(sqlite3.connect((directory / "intent.sqlite").resolve().as_uri()+"?mode=ro", uri=True)) as db:
        entries = db.execute("SELECT id,request_sha,state,raw_sha,audit_sha FROM intents").fetchall()
        run = db.execute("SELECT digest,state,binding FROM remaining_run").fetchone()
    if (node not in (1243,130) or len(entries) != 1 or entries[0][0] != f"{version}:{node}:compare" or entries[0][2] != "REJECTED"
            or run[1] != "HALTED_REVIEW_REQUIRED_NO_RETRY" or canary.sha(run[2]) != run[0]
            or canary.strict_json(run[2]) != approval["binding"]
            or context["contract_binding"] != run[0] or context["identity"] != entries[0][0]
            or context["dependency"] != lineage
            or context["request_sha256"] != canary.sha(encoded(payload))
            or entries[0][1] != context["request_sha256"]
            or context["wire_sha256"] != canary.sha(prior.wire_for(payload))):
        raise ValueError("Prior comparison ledger/request binding differs")
    raw = bytes.fromhex(provider["raw_hex"])
    if (provider["http_status"] != 200 or not provider["body_complete"] or provider["secret_echo_redacted"]
            or canary.sha(raw) != provider["original_response_sha256"]
            or canary.sha(raw) != provider["persisted_response_sha256"]
            or provider["context_sha256"] != canary.sha(canonical_bytes(context))):
        raise ValueError("Prior comparison response integrity failure")
    envelope = canary.strict_json(raw)
    valid_identity = envelope["model"] in identity_policy.MODELS if node == 130 else envelope["model"] == prior.REVISION
    if not valid_identity or len(envelope["choices"]) != 1 or envelope["choices"][0]["finish_reason"] != "stop":
        raise ValueError("Unexpected prior comparison envelope")
    content = envelope["choices"][0]["message"]["content"]
    receipt = records[entries[0][4]]
    if (entries[0][3] != canary.sha(content.encode()) or receipt["raw_sha256"] != entries[0][3]
            or receipt["request_sha256"] != entries[0][1]
            or bytes.fromhex(receipt["raw_hex"]) != content.encode() or receipt["reason"] != "L1_QUOTE_NOT_FOUND"):
        raise ValueError("Prior comparison rejection receipt differs")
    value = canary.strict_json(content)
    from ..sara3.evidence import EvidenceError
    try:
        validate_result(value, payload["target"]["text"])
    except EvidenceError as error:
        if error.code != "L1_QUOTE_NOT_FOUND":
            raise ValueError("Prior comparison failure changed") from None
    else:
        raise ValueError("Unexpected reclassification of failed comparison")
    return {"state": "REJECTED", "historical": True, "http_status": 200, "parse_status": "PASS",
            "l1_status": "FAIL", "reason": "L1_QUOTE_NOT_FOUND", "usage": envelope.get("usage"),
            "provider_model": envelope["model"], "provider_receipt": provider_id,
            "request_receipt": context_id, "response_sha256": canary.sha(raw),
            "accepted_label": None, "l2_status": "NOT_ASSESSED"}


def reassess_130(root, blind):
    directory = root / ".local_artifacts" / FOUR_DIRECTORY
    records = prior._read_receipts(directory)
    provider_id, provider = _one(records, "kind", "canary_provider_response")
    context_id, context = _one(records, "kind", "outstanding_request")
    _, approval = _one(records, "kind", "outstanding_approval")
    with closing(sqlite3.connect((directory / "intent.sqlite").resolve().as_uri()+"?mode=ro", uri=True)) as db:
        entries = db.execute("SELECT id,request_sha,state,raw_sha,audit_sha FROM intents").fetchall()
        run = db.execute("SELECT digest,state,binding FROM remaining_run").fetchone()
    if (len(entries) != 1 or entries[0][0] != FOUR_VERSION+":130:blind" or entries[0][2] != "REJECTED"
            or run[1] != "HALTED_REVIEW_REQUIRED_NO_RETRY" or canary.sha(run[2]) != run[0]
            or canary.strict_json(run[2]) != approval["binding"] or context["contract_binding"] != run[0]
            or context["identity"] != entries[0][0] or context["request_sha256"] != entries[0][1]
            or entries[0][1] != canary.sha(encoded(blind))
            or context["wire_sha256"] != canary.sha(prior.wire_for(blind))):
        raise ValueError("Preserved130 ledger/request mismatch")
    raw = bytes.fromhex(provider["raw_hex"])
    if (provider["http_status"] != 200 or not provider["body_complete"] or provider["secret_echo_redacted"]
            or canary.sha(raw) != provider["original_response_sha256"]
            or canary.sha(raw) != provider["persisted_response_sha256"]
            or provider["context_sha256"] != canary.sha(canonical_bytes(context))):
        raise ValueError("Preserved130 raw response mismatch")
    envelope = canary.strict_json(raw)
    settings = {"temperature": 1, "n": 1, "max_tokens": 512, "reasoning_effort": "OMITTED"}
    if (not identity_policy.allowed("GapGPT", prior.ENDPOINT, prior.MODEL, envelope.get("model"), settings)
            or len(envelope["choices"]) != 1 or envelope["choices"][0]["finish_reason"] != "stop"):
        raise ValueError("Preserved130 identity/envelope invalid")
    content = envelope["choices"][0]["message"]["content"]
    receipt = records[entries[0][4]]
    if (receipt["reason"] != "RETURNED_MODEL_MISMATCH" or receipt["request_sha256"] != entries[0][1]
            or receipt["raw_sha256"] != entries[0][3] or canary.sha(raw) != entries[0][3]
            or bytes.fromhex(receipt["raw_hex"]) != raw):
        raise ValueError("Preserved130 rejection binding invalid")
    value = canary.strict_json(content)
    result = validate_result(value, blind["target"]["text"])
    return {"state": "HISTORICAL_REJECTED_DIAGNOSTIC_PASS", "historical": True,
        "original_ledger_state": "REJECTED", "original_reason": "RETURNED_MODEL_MISMATCH",
        "http_status": 200, "parse_status": "PASS", "identity_status": "OWNER_APPROVED_PROVIDER_REPORTED",
        "identity_policy": identity_policy.VERSION, "provider_model": envelope["model"],
        "l1_status": result["l1_status"], "abstain": result["abstain"], "class_index": result["class_index"],
        "usage": envelope.get("usage"), "accepted_label": None, "l2_status": "NOT_ASSESSED",
        "lineage": {"provider_receipt": provider_id, "request_receipt": context_id,
            "readiness_receipt": entries[0][4], "response_sha256": canary.sha(raw),
            "inner_response_sha256": canary.sha(content.encode()), "request_sha256": entries[0][1],
            "wire_sha256": context["wire_sha256"], "batch_digest": run[0]}}


def prepare(root=ROOT, *, four_only=False, post130=False, blind_only=False):
    post130 = post130 or blind_only
    four_only = four_only or post130
    requests, first = prior.sealed_inputs(root)
    preserved = preserved_1243(root, requests[1243][0])
    plan = []
    historical_comparison = None
    if four_only:
        historical_comparison = rejected_comparison(root, materialize_comparison(requests[1243][1], preserved["class_index"]), preserved["lineage"])
    preserved130 = None
    if post130:
        preserved130 = reassess_130(root, requests[130][0])
        diagnostic_id, diagnostic = _one(prior._read_receipts(root / ".local_artifacts/gapgpt_130_identity_reassessment"),
                                        "schema", "sara.identity.diagnostic_reassessment.v1")
        if (diagnostic["outcome"] != preserved130 or diagnostic["identity_policy"] != identity_policy.VERSION
                or diagnostic["policy_sha256"] != canary.sha((root / "src/llmgnn_sara/pilot/identity.py").read_bytes())):
            raise ValueError("Preserved130 diagnostic mismatch")
        preserved130["lineage"]["diagnostic_receipt"] = diagnostic_id
        if not blind_only and not preserved130["abstain"]:
            plan.append({"node":130,"phase":"compare","conditional":False,
                "payload":materialize_comparison(requests[130][1],preserved130["class_index"]),
                "dependency":preserved130["lineage"]})
    elif not four_only and not preserved["abstain"]:
        plan.append({"node": 1243, "phase": "compare", "conditional": False,
            "payload": materialize_comparison(requests[1243][1], preserved["class_index"]),
            "dependency": preserved["lineage"]})
    for node in (NODES[1:] if post130 else NODES):
        plan.append({"node": node, "phase": "blind", "conditional": False, "payload": requests[node][0]})
        if not blind_only:
            plan.append({"node": node, "phase": "compare", "conditional": True, "payload": requests[node][1]})
    possible = [materialize_comparison(s["payload"], label) for s in plan if s["conditional"] for label in range(7)]
    possible += [s["payload"] for s in plan if not s["conditional"]]
    version = BLIND_VERSION if blind_only else ALIAS_VERSION if post130 else FOUR_VERSION if four_only else VERSION
    prior.verify_no_prior_dispatch(root, possible, reserved_prefix=version)
    for payload in possible:
        prior.wire_for(payload)
    runtime = ["pilot/outstanding_gapgpt.py", "pilot/remaining_gapgpt.py", "pilot/canary.py",
               "pilot/readiness.py", "pilot/protocol.py", "sara3/audit.py", "sara3/evidence.py"]
    if four_only:
        runtime.append("pilot/four_gapgpt.py")
    if post130:
        runtime.extend(("pilot/identity.py", "pilot/post130_gapgpt.py"))
    if blind_only:
        runtime.append("pilot/blind_only_gapgpt.py")
    contract = {"version": version, "provider": "GapGPT", "endpoint": prior.ENDPOINT, "model": prior.MODEL,
        "allowed_returned_revision": prior.REVISION, "identity_provenance": prior.CONTRACT["identity_provenance"],
        "temperature": 1, "n": 1, "max_tokens": 512, "reasoning_effort": "OMITTED", "l1_rule": RULE,
        "amendment": "POST_OBSERVATION_1243_COMPARISON_ELIGIBILITY_NOT_ORIGINAL_ACCEPTANCE",
        "plan": plan, "preserved_1243": preserved, "preserved_637": first,
        "maximum_calls": len(plan), "input_per_call": 16384, "output_per_call": 512,
        "local_reservation_usd": "0.10", "seals": list(canary.SEALS), "retries": 0,
        "resume": "FORBIDDEN", "accepted_label": None, "l2_status": "NOT_ASSESSED",
        "source_manifest_sha256": canary.sha((root / "manifests/recovered_sources.json").read_bytes()),
        "runtime_hashes": {name: canary.sha((root / "src/llmgnn_sara" / name).read_bytes()) for name in runtime}}
    if four_only:
        contract["preserved_1243_comparison"] = historical_comparison
        contract["amendment"] = "OWNER_APPROVED_PROCEED_AFTER_RECORDED_COMPARISON_FAILURE_NO_RETRY"
    if post130:
        contract.update(preserved_130=preserved130, identity_policy=identity_policy.VERSION,
                        allowed_returned_models=list(identity_policy.MODELS),
                        amendment="OWNER_APPROVED_EXACT_ALIAS_RESTORATION_POST130_COMPARISON_NOT_ORIGINAL_ACCEPTANCE")
    if blind_only:
        contract["preserved_130_comparison"] = rejected_comparison(root,
            materialize_comparison(requests[130][1],preserved130["class_index"]),preserved130["lineage"],node=130)
        contract["amendment"] = "POST_OBSERVATION_BLIND_ONLY_NOT_COMPLETION_OF_ORIGINAL_PAIRED_PROTOCOL"
    return contract


def approvals_for(contract):
    return {"amendment": True, "privacy": True, "outstanding_list": True, "declared_limits": True,
            "reservation_usd": "0.10", "dispatch": contract["version"],
            "contract_sha256": canary.sha(canonical_bytes(contract))}


def start(contract, approval, ledger, audit):
    if approval != approvals_for(contract) or any(approval.get(k) is not True for k in
            ("amendment", "privacy", "outstanding_list", "declared_limits")):
        raise ValueError("Fresh amended-contract approvals required")
    blind_only = contract["version"] == BLIND_VERSION
    post130 = contract["version"] in (ALIAS_VERSION,BLIND_VERSION)
    four_only = contract["version"] in (FOUR_VERSION, ALIAS_VERSION,BLIND_VERSION)
    if four_only and (contract.get("preserved_1243_comparison", {}).get("state") != "REJECTED"
                      or contract["preserved_1243_comparison"].get("historical") is not True):
        raise ValueError("Prior comparison failure must remain historical")
    expected = ([] if four_only or contract["preserved_1243"]["abstain"] else [(1243, "compare", False)])
    if post130:
        if contract.get("identity_policy") != identity_policy.VERSION or contract.get("allowed_returned_models") != list(identity_policy.MODELS):
            raise ValueError("Unknown identity policy")
        expected = [] if contract["preserved_130"]["abstain"] else [(130,"compare",False)]
    expected += [(node, phase, phase == "compare") for node in (NODES[1:] if post130 else NODES) for phase in ("blind", "compare")]
    if blind_only:
        if (contract.get("preserved_130_comparison",{}).get("state") != "REJECTED"
                or contract["preserved_130_comparison"].get("historical") is not True):
            raise ValueError("Prior130 comparison failure must remain immutable history")
        expected = [(node,"blind",False) for node in NODES[1:]]
    if (contract["version"] not in (VERSION, FOUR_VERSION, ALIAS_VERSION,BLIND_VERSION) or contract["l1_rule"] != RULE
            or [(s["node"], s["phase"], s["conditional"]) for s in contract["plan"]] != expected
            or contract["maximum_calls"] != len(expected) or contract["local_reservation_usd"] != "0.10"
            or (contract["provider"], contract["endpoint"], contract["model"], contract["allowed_returned_revision"])
               != ("GapGPT", prior.ENDPOINT, prior.MODEL, prior.REVISION)
            or (contract["temperature"], contract["n"], contract["max_tokens"], contract["reasoning_effort"])
               != (1, 1, 512, "OMITTED")):
        raise ValueError("Invalid continuation contract")
    for step in contract["plan"]:
        if step["node"] == 637 or (step["node"] == 1243 and step["phase"] != "compare"):
            raise ValueError("Preserved blind redispatch forbidden")
    binding = {"contract": contract, "approval": approval}
    receipt = audit.write({"kind": "outstanding_approval", "binding": binding})
    audit.read(receipt)
    digest = canary.sha(canonical_bytes(binding))
    with closing(sqlite3.connect(ledger.path)) as db, db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT count(*) FROM intents").fetchone()[0]:
            raise ValueError("Existing intents; no resume")
        db.execute("CREATE TABLE IF NOT EXISTS remaining_run (id INTEGER PRIMARY KEY CHECK(id=1), digest TEXT, state TEXT, binding BLOB, next_ordinal INTEGER NOT NULL DEFAULT 0)")
        if db.execute("SELECT count(*) FROM remaining_run").fetchone()[0]:
            raise ValueError("Continuation already started; no resume")
        db.execute("INSERT INTO remaining_run VALUES (1,?,'RUNNING',?,0)", (digest, canonical_bytes(binding)))
    return digest


def _advance(ledger, digest, ordinal):
    with closing(sqlite3.connect(ledger.path)) as db, db:
        db.execute("PRAGMA synchronous=FULL")
        changed = db.execute("UPDATE remaining_run SET next_ordinal=? WHERE id=1 AND digest=? AND state='RUNNING' AND next_ordinal=?",
                             (ordinal+1, digest, ordinal)).rowcount
        if changed != 1:
            raise ValueError("Wrong continuation cursor/state")


def dispatch(contract, ordinal, payload, dependency, key, ledger, audit, digest, *, transport=None):
    if type(ordinal) is not int or not 0 <= ordinal < len(contract["plan"]):
        raise ValueError("Wrong step ordinal")
    step = contract["plan"][ordinal]
    expected = step["payload"]
    if step["conditional"]:
        prior_id = f"{contract['version']}:{step['node']}:blind"
        with closing(sqlite3.connect(ledger.path)) as db:
            entry = db.execute("SELECT id,state,audit_sha FROM intents ORDER BY rowid DESC LIMIT 1").fetchone()
        if not entry or entry[:2] != (prior_id, "COMPLETED"):
            raise ValueError("Comparison requires completed blind")
        raw = bytes.fromhex(audit.read(entry[2])["raw_hex"])
        value = canary.strict_json(raw)
        validated = validate_result(value, expected["target"]["text"])
        if validated["abstain"] or type(dependency) is not dict or dependency.get("blind_response_sha256") != canary.sha(raw):
            raise ValueError("Comparison abstention/hash mismatch")
        provider_record = audit.read(dependency["blind_provider_receipt"])
        provider_content = canary.strict_json(bytes.fromhex(provider_record["raw_hex"]))["choices"][0]["message"]["content"]
        if provider_content.encode() != raw or dependency["template_sha256"] != canary.sha(canonical_bytes(expected)):
            raise ValueError("Comparison provider/template mismatch")
        expected = materialize_comparison(expected, validated["class_index"])
    elif step["node"] == 1243 and dependency != contract["preserved_1243"]["lineage"]:
        raise ValueError("Preserved blind lineage mismatch")
    elif step["node"] == 130 and contract["version"] == ALIAS_VERSION and dependency != contract["preserved_130"]["lineage"]:
        raise ValueError("Preserved130 lineage mismatch")
    if payload != expected or payload["node_id"] != step["node"] or payload["phase"] != step["phase"]:
        raise ValueError("Outstanding request mismatch")
    if type(key) is not str or not 12 <= len(key) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("Invalid credential format")
    with closing(sqlite3.connect(ledger.path)) as db:
        bound = db.execute("SELECT digest,state,binding,next_ordinal FROM remaining_run WHERE id=1").fetchone()
        if (not bound or bound[:2] != (digest, "RUNNING") or canary.sha(bound[2]) != digest
                or canary.strict_json(bound[2])["contract"] != contract or bound[3] != ordinal):
            raise ValueError("Wrong contract binding/state")
        count, inputs, outputs = db.execute("SELECT count(*),coalesce(sum(input_cap),0),coalesce(sum(output_cap),0) FROM intents").fetchone()
        if count >= contract["maximum_calls"] or inputs+16384 > len(contract["plan"])*16384 or outputs+512 > len(contract["plan"])*512:
            raise ValueError("Outstanding reservation exhausted")
    identity = f"{contract['version']}:{step['node']}:{step['phase']}"
    wire = prior.wire_for(payload)
    context = {"kind": "outstanding_request", "ordinal": ordinal, "identity": identity,
               "contract_binding": digest, "request_sha256": canary.sha(encoded(payload)),
               "wire_sha256": canary.sha(wire), "dependency": dependency, "l1_rule": RULE}
    audit.read(audit.write(context))
    ledger.reserve(identity, payload, 16384, 512)
    ledger.mark_dispatched(identity, payload)
    result = canary._dispatch_recorded(payload, wire, key, audit, ledger, identity,
        canary.sha(canonical_bytes(context)), transport=transport, target="account-panel-temperature1",
        model_check=lambda model: identity_policy.allowed(contract["provider"],contract["endpoint"],contract["model"],model,
            {k:contract[k] for k in ("temperature","n","max_tokens","reasoning_effort")})
            if contract["version"] in (ALIAS_VERSION,BLIND_VERSION) else model == prior.REVISION and prior.identity_allowed("GapGPT", prior.ENDPOINT, prior.MODEL, model))
    outcome = prior.phase_outcome(result, audit, payload)
    if outcome["state"] == "COMPLETED":
        _advance(ledger, digest, ordinal)
    return outcome


def run(contract, key, ledger, audit, digest, *, transport=None):
    if ledger.snapshot():
        raise ValueError("Existing intent; no restart")
    rows = [contract["preserved_637"], {"node": 1243, "blind": contract["preserved_1243"],
            "compare": contract.get("preserved_1243_comparison", {"state": "NOT_ATTEMPTED" if not contract["preserved_1243"]["abstain"] else "NOT_PERMITTED_BLIND_ABSTENTION"})}]
    rows += [{"node": node, "blind": {"state": "NOT_ATTEMPTED"}, "compare": {"state": "NOT_ATTEMPTED"}} for node in NODES]
    if contract["version"] in (ALIAS_VERSION,BLIND_VERSION):
        rows[2]["blind"] = contract["preserved_130"]
        if contract["preserved_130"]["abstain"]:
            rows[2]["compare"] = {"state":"NOT_PERMITTED_BLIND_ABSTENTION"}
    if contract["version"] == BLIND_VERSION:
        rows[2]["compare"] = contract["preserved_130_comparison"]
        for row in rows[3:]:
            row["compare"] = {"state":"NOT_PERMITTED_BLIND_ONLY_AMENDMENT"}
    summary = {"version": contract["version"], "batch_digest": digest, "rows": rows,
               "historical_1243_blind_included_in_new_totals": False,
               "historical_130_blind_included_in_new_totals": False if contract["version"] in (ALIAS_VERSION,BLIND_VERSION) else None,
               "paired_protocol_complete": False,
               "original_cohort_size": 6, "maximum_new_dispatches": contract["maximum_calls"],
               "accepted_label": None, "l2_status": "NOT_ASSESSED"}
    try:
        for ordinal, step in enumerate(contract["plan"]):
            row = next(r for r in rows if r["node"] == step["node"])
            payload = step["payload"]
            dependency = step.get("dependency")
            if step["conditional"]:
                if row["blind"]["state"] != "COMPLETED":
                    raise ValueError("Invalid conditional predecessor")
                if row["blind"]["abstain"]:
                    row["compare"] = {"state": "NOT_PERMITTED_BLIND_ABSTENTION"}
                    _advance(ledger, digest, ordinal)
                    continue
                payload = materialize_comparison(payload, row["blind"]["class_index"])
                blind_record = audit.read(row["blind"]["provider_receipt"])
                content = canary.strict_json(bytes.fromhex(blind_record["raw_hex"]))["choices"][0]["message"]["content"]
                dependency = {"blind_provider_receipt": row["blind"]["provider_receipt"],
                              "blind_response_sha256": canary.sha(content.encode()),
                              "template_sha256": canary.sha(canonical_bytes(step["payload"]))}
            row[step["phase"]] = dispatch(contract, ordinal, payload, dependency, key, ledger, audit, digest, transport=transport)
            audit.read(audit.write({"kind": "outstanding_progress", "summary": summary}))
            if row[step["phase"]]["state"] != "COMPLETED":
                raise ValueError("Response failed; halt")
        state = "FINISHED"
    except BaseException:
        state = "HALTED_REVIEW_REQUIRED_NO_RETRY"
    entries = ledger.snapshot()
    summary["new_phase_denominators"] = {phase: sum(r[0].endswith(":"+phase) for r in entries)
                                         for phase in ("blind", "compare")}
    summary["new_nodes_with_intents"] = len({r[0].split(":")[-2] for r in entries})
    return prior.finish_summary(summary, ledger, audit, digest, state)


def main(*, four_only=False, post130=False, blind_only=False):
    try:
        if len(sys.argv) != 1 or not sys.stdin.isatty():
            raise ValueError("Fresh local terminal approvals required")
        contract = prepare(four_only=four_only,post130=post130,blind_only=blind_only)
        directory = BLIND_DIRECTORY if blind_only else ALIAS_DIRECTORY if post130 else FOUR_DIRECTORY if four_only else DIRECTORY
        version = contract["version"]
        audit = PrivateAudit(ROOT / ".local_artifacts" / directory)
        ledger = ReadinessLedger(audit.root / "intent.sqlite")
        with closing(sqlite3.connect(ledger.path)) as db:
            if db.execute("SELECT count(*) FROM sqlite_master WHERE name='remaining_run'").fetchone()[0] or ledger.snapshot():
                raise ValueError("Continuation already started; no restart")
        print(f"GapGPT | {prior.ENDPOINT} | {prior.MODEL} | provider-reported only")
        print("Allowed exact returned identifiers: " + ", ".join(contract.get("allowed_returned_models",[prior.REVISION])))
        print("temperature1/n1/max_tokens512; reasoning_effort omitted; L1 " + RULE)
        print("Post-observation L1 amendment; original REJECTED states stay unchanged. No637/1243 blind.")
        if four_only:
            print("FOUR NEVER-ATTEMPTED NODES ONLY. No1243 comparison retry; preserve that failure.")
        if post130:
            print("POST130 IDENTITY AMENDMENT: no130 blind retry; original REJECTED preserved.")
        if blind_only:
            print("BLIND ONLY:682,2396,653. NO COMPARISONS. Post-observation amendment, not paired completion.")
        print("Outstanding list (comparison entries after new blinds are conditional):")
        for s in contract["plan"]:
            print(f"node{s['node']} {s['phase']}" + (" IF ELIGIBLE" if s["conditional"] else ""))
        cap = contract["maximum_calls"]
        print(f"Max{cap} new calls; declared input{cap*16384}/output{cap*512}; no retry/resume.")
        print("Byte preflight is not vendor tokenization; usage/prices are not verified billing.")
        print(f"Provisional estimate USD{cap*.0018944:.7f}; fresh USD0.10 reservation, NOT provider billing guarantee.")
        approval = {"contract_sha256": canary.sha(canonical_bytes(contract))}
        for field, phrase in (("amendment", "APPROVE BLIND ONLY AMENDMENT V1" if blind_only else "APPROVE EXACT IDENTITY POLICY V1" if post130 else "APPROVE POST-OBSERVATION L1 CONTINUATION"),
                              ("privacy", "APPROVE CONTINUATION PRIVACY"),
                              ("outstanding_list", "APPROVE EXACT OUTSTANDING LIST"),
                              ("declared_limits", "APPROVE OUTSTANDING DECLARED LIMITS")):
            approval[field] = input("Type " + phrase + ": ") == phrase
            if not approval[field]:
                raise ValueError("Approval declined")
        approval["reservation_usd"] = input("Confirm fresh aggregate reservation; type 0.10: ")
        if approval["reservation_usd"] != "0.10":
            raise ValueError("Budget declined")
        key = canary.credential()
        approval["dispatch"] = input("Authorize outstanding requests; type " + version + ": ")
        if prepare(four_only=four_only,post130=post130,blind_only=blind_only) != contract:
            raise ValueError("Inputs/state changed during approvals")
        digest = start(contract, approval, ledger, audit)
        summary, _ = run(contract, key, ledger, audit, digest)
        print(json.dumps({k: summary[k] for k in ("state", "dispatch_attempts_upper_bound", "state_counts")}))
        print("Private results: .local_artifacts/" + directory + "; never rerun after start.")
        return 0 if summary["state"] == "FINISHED" else 1
    except BaseException:
        print("Continuation blocked/interrupted; no retry/resume. Inspect private ledger.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
