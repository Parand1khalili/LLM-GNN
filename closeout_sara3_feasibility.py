"""SARA-3 six-node feasibility closeout and PRIVATE blinded L2 intake.

Run ONCE from the existing llm-gnn checkout, using the project virtualenv:
  .venv\\Scripts\\python.exe -B closeout_sara3_feasibility.py

No network/API, secrets, GT, training, execution, retries, or historical ledger writes.
The only writes are new Git-ignored, owner-private closeout/reviewer artifacts.
Uses actual authenticated inputs and immutable local response receipts; refuses
partial or unexpected states rather than inventing results.
"""
from __future__ import annotations

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys

SCHEMA = "sara3.feasibility.closeout.v1.1"
NODES = (637, 1243, 130, 682, 2396, 653)
HUMAN_NODES = (1243, 130, 682)
ORIGINAL = {
    (637, "blind"): ("gapgpt_app_t1_canary_637", "REJECTED", "INVALID_ENVELOPE_OR_USAGE"),
    (1243, "blind"): ("gapgpt_remaining_pilot_v1", "REJECTED", "L1_QUOTE_NOT_FOUND"),
    (1243, "compare"): ("gapgpt_outstanding_l1_v1", "REJECTED", "L1_QUOTE_NOT_FOUND"),
    (130, "blind"): ("gapgpt_four_unattempted_v1", "REJECTED", "RETURNED_MODEL_MISMATCH"),
    (130, "compare"): ("gapgpt_post130_v1", "REJECTED", "L1_QUOTE_NOT_FOUND"),
    (682, "blind"): ("gapgpt_three_blind_only_v1", "COMPLETED", "L1_PASS_L2_NOT_ASSESSED"),
    (2396, "blind"): ("gapgpt_three_blind_only_v1", "COMPLETED", "L1_PASS_L2_NOT_ASSESSED"),
    (653, "blind"): ("gapgpt_three_blind_only_v1", "REJECTED", "L1_QUOTE_NOT_FOUND"),
}
EXPECTED_IDENTITIES = {
    (637, "blind"): "gapgpt-app-t1-blind-637-canary-v1",
    (1243, "blind"): "gapgpt-six-node-remaining-t1-v1:1243:blind",
    (1243, "compare"): "gapgpt-outstanding-l1-wrapper-v1:1243:compare",
    (130, "blind"): "gapgpt-four-unattempted-v1:130:blind",
    (130, "compare"): "gapgpt-post130-exact-identities-v1:130:compare",
    (682, "blind"): "gapgpt-three-blind-only-v1:682:blind",
    (2396, "blind"): "gapgpt-three-blind-only-v1:2396:blind",
    (653, "blind"): "gapgpt-three-blind-only-v1:653:blind",
}
ALLOWED_MODELS = frozenset(("gpt-6-luna", "gpt-6-luna-2026-09-22"))
# When rejection happens before extracting the assistant content, ReadinessLedger
# stores the whole provider envelope, not the extracted inner content.
PRE_CONTENT_REJECTION_REASONS = frozenset(("INVALID_ENVELOPE_OR_USAGE", "RETURNED_MODEL_MISMATCH"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError("Duplicate JSON key")
            obj[k] = v
        return obj
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def receipt_dir(path: Path):
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Missing or unsafe private store: {path.name}")
    result = {}
    for item in path.glob("*.json"):
        if item.is_symlink() or len(item.stem) != 64 or any(c not in '0123456789abcdef' for c in item.stem):
            raise ValueError(f"Unsafe receipt filename: {path.name}")
        if item.stat().st_size > 10_000_000:
            raise ValueError("Receipt size limit")
        raw = item.read_bytes()
        if sha(raw) != item.stem:
            raise ValueError("Immutable receipt hash mismatch")
        result[item.stem] = strict_json(raw)
    if not result:
        raise ValueError("Empty private receipt store")
    return result


def ro_ledger(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or unsafe ledger")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        entries = db.execute("SELECT id,request_sha,state,raw_sha,audit_sha FROM intents ORDER BY rowid").fetchall()
        has_run = db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='remaining_run'").fetchone()[0]
        run = db.execute("SELECT digest,state,binding FROM remaining_run WHERE id=1").fetchone() if has_run else None
    if run:
        if sha(run[2]) != run[0] or run[1] != "HALTED_REVIEW_REQUIRED_NO_RETRY":
            raise ValueError("Unexpected batch terminal state / digest")
        binding = strict_json(run[2])
        if type(binding) is not dict or "contract" not in binding:
            raise ValueError("Incomplete batch binding")
    return entries, run


def find_one(records, **fields):
    found = [(k, v) for k, v in records.items()
             if all(isinstance(v, dict) and v.get(f) == val for f, val in fields.items())]
    if len(found) != 1:
        raise ValueError("Missing or ambiguous immutable receipt")
    return found[0]


def assert_readiness_raw_binding(original_reason: str, readiness_raw: bytes, envelope_raw: bytes, content: str):
    """Check immutable readiness bytes against the appropriate parser stage."""
    if type(content) is not str or type(readiness_raw) is not bytes or type(envelope_raw) is not bytes:
        raise ValueError("Original readiness content types invalid")
    expected = envelope_raw if original_reason in PRE_CONTENT_REJECTION_REASONS else content.encode("utf-8")
    if readiness_raw != expected:
        raise ValueError("Original readiness content mismatch")


def diagnostic_kind(target: str, quote: str, quote_match):
    """Diagnostic only. Never changes L1 acceptance."""
    normalized = quote_match(quote)
    if normalized in target:
        return "EXACT_AFTER_APPROVED_WRAPPER"
    if normalized and normalized[0].swapcase() + normalized[1:] in target:
        return "INITIAL_CHARACTER_CASE_ONLY"
    return "NON_EXACT_OTHER"


def make_response_form(case_id: str, nquotes: int):
    return {"schema": "sara3.l2.human.response.v1", "reviewer_case_id": case_id,
            "reviewer_independence_confirmed": None,
            "each_quote_supports_proposed_primary_class": [None] * nquotes,
            "overall_semantic_support": None,
            "primary_topic_match": None,
            "uncertainty_or_limitation": "",
            "short_justification": "",
            "allowed_values": {"each_quote_supports_proposed_primary_class": ["supports", "does_not_support", "uncertain"],
                               "overall_semantic_support": ["supports", "does_not_support", "uncertain"],
                               "primary_topic_match": ["yes", "no", "uncertain"]}}


def public_report(rows, *, estimated_cost, usage):
    assert len(rows) == 8
    by = {(r["node"], r["phase"]): r for r in rows}
    assert set(by) == set(ORIGINAL)
    primary_pass = sum(by[n, "blind"]["original_ledger_state"] == "COMPLETED" for n in NODES)
    diagnostic_pass = sum(by[n, "blind"]["replayed_l1"] == "PASS" for n in NODES)
    abstentions = sum(by[n, "blind"]["abstain"] for n in NODES)
    eligible = sum(by[n, "blind"]["replayed_l1"] == "PASS" and not by[n, "blind"]["abstain"] for n in NODES)
    totals = "unknown" if not usage else f"{usage['prompt_tokens']} input + {usage['completion_tokens']} output (reasoning included if reported)"
    return f"""# SARA-3 — Six-node Feasibility Closeout (Persian)

Schema: `{SCHEMA}`  
Status: **CLOSED_FOR_LIVE_REQUESTS; L2 NOT_ASSESSED; ACCEPTED LABELS = 0**  
Source: locally verified private immutable receipts and sealed inputs; this report excludes private texts, labels, and raw responses.

## Verified execution outcomes

- Six selected blind nodes: **6/6 authenticated HTTP 200 / parseable responses** (NOT six originally accepted L1 results).
- Original ledger `COMPLETED` blind outcomes: **{primary_pass}/6**.
- L1-valid blind outcomes under current rules, including separately documented post-observation reassessments: **{diagnostic_pass}/6**. These are *descriptive*, not original acceptance.
- Blind abstentions: **{abstentions}/6**.
- Non-abstaining L1-valid blind outputs for **human review only**: **{eligible}/6**.
- Comparison attempts: **2**, both originally `REJECTED` for L1 exact-quotation failure; no completion of paired protocol.
- Untested comparisons remain explicitly not attempted (four nodes including abstentions; only two comparisons were attempted).
- New pilot requests must not be repeated. Historical ledgers are retained.

## Per-node ledger/diagnostic distinction

| Node | Blind original ledger | Blind replay under current L1 | Abstain | Comparison original |
|---|---|---|---|---|
""" + "\n".join(
        f"| {n} | {by[n,'blind']['original_ledger_state']} ({by[n,'blind']['original_reason']}) | {by[n,'blind']['replayed_l1']} | {'yes' if by[n,'blind']['abstain'] else 'no'} | " +
        (f"{by[n,'compare']['original_ledger_state']} ({by[n,'compare']['original_reason']})" if (n, 'compare') in by else "not attempted") + " |"
        for n in NODES) + f"""

## Usage / financial limitation

Provider-reported usage across all eight preserved responses: {totals}.  
Provisional estimated cost using owner-supplied $0.10/M input and $0.50/M output: **USD {estimated_cost}**; **NOT** verified provider billing. Cache-specific charges may differ.

## Interpretation

- A syntactically valid HTTP/JSON response is not the same as an L1-valid answer.
- Case-only failures remain failures under the case-sensitive protocol, even where semantic meaning may be unchanged.
- Node 637's original audited readiness reason is `INVALID_ENVELOPE_OR_USAGE`, an umbrella pre-L1 rejection. Its underlying cause cannot be established from that code alone; never substitute a presumed model mismatch for the recorded reason.
- Post-observation quote-wrapper/identity-policy reassessments must be reported separately from original terminal outcomes.
- Two comparison failures are not a reliable population error rate; selected comparisons are conditional on blind outcomes.
- L1 proves lexical quotation provenance, not semantic support for the claimed primary paper class.
- This feasibility sample of six is not an independent confirmatory accuracy study. No GT was accessed or GCN trained here.
- All L2 judgments remain **NOT_ASSESSED**. Require two independent, blinded human assessments per eligible output before any semantic decision; this closeout never promotes training labels.
- Blind-only completion after observed comparison problems is a **post-observation amendment**, not the original paired design.
"""


def load_verified(root: Path):
    # Project modules enforce sealed authentic inputs and production L1 semantics.
    from llmgnn_sara.pilot import canary, remaining_gapgpt as prior, outstanding_gapgpt as current
    from llmgnn_sara.pilot.protocol import materialize_comparison
    from llmgnn_sara.pilot.readiness import encoded
    from llmgnn_sara.sara3.evidence import EvidenceError, validate_result, quote_for_matching

    if canary.ROOT.resolve() != root.resolve():
        raise ValueError("This script must run inside the authenticated project checkout")
    requests, _ = prior.sealed_inputs(root)
    prior.prior_637(root)
    b1243 = current.preserved_1243(root, requests[1243][0])
    b130 = current.reassess_130(root, requests[130][0])
    if b1243["abstain"] or b130["abstain"] or b1243["class_index"] != 5:
        raise ValueError("Preserved blind outcomes differ from reviewed pilot")
    # Verify versioned 130 reassessment rather than silently accepting historical REJECTED.
    diag = receipt_dir(root / ".local_artifacts/gapgpt_130_identity_reassessment")
    _, rec = find_one(diag, schema="sara.identity.diagnostic_reassessment.v1")
    from llmgnn_sara.pilot import identity as policy
    if (rec.get("outcome") != b130 or rec.get("identity_policy") != policy.VERSION
            or rec.get("policy_sha256") != sha((root / "src/llmgnn_sara/pilot/identity.py").read_bytes())):
        raise ValueError("130 diagnostic provenance mismatch")
    c1243 = materialize_comparison(requests[1243][1], b1243["class_index"])
    current.rejected_comparison(root, c1243, b1243["lineage"])
    c130 = materialize_comparison(requests[130][1], b130["class_index"])
    payloads = {(n, 'blind'): requests[n][0] for n in NODES if n != 637}
    payloads[(637, 'blind')] = canary.prepare(target='account-panel-temperature1')[0]
    payloads[(1243, 'compare')] = c1243
    payloads[(130, 'compare')] = c130
    dirs = {}
    for d in {v[0] for v in ORIGINAL.values()}:
        p = root / '.local_artifacts' / d
        records = receipt_dir(p)
        entries, run = ro_ledger(p / 'intent.sqlite')
        dirs[d] = (records, entries, run)
    # The six known stores have an exact intent distribution: 1+1+1+1+1+3.
    # Canaries at other wire settings are not asserted to be absent.
    counts = {d: len(v[1]) for d, v in dirs.items()}
    if counts != {'gapgpt_app_t1_canary_637':1,'gapgpt_remaining_pilot_v1':1,
                  'gapgpt_outstanding_l1_v1':1,'gapgpt_four_unattempted_v1':1,
                  'gapgpt_post130_v1':1,'gapgpt_three_blind_only_v1':3}:
        raise ValueError("Unexpected intent counts; manual review required")
    final_three = dirs['gapgpt_three_blind_only_v1'][1]
    if [r[0] for r in final_three] != [EXPECTED_IDENTITIES[(n,'blind')] for n in (682,2396,653)]:
        raise ValueError("Unexpected final blind dispatch order")

    rows = []
    private = {}
    for key in ORIGINAL:
        node, phase = key
        dirname, expected_state, expected_reason = ORIGINAL[key]
        records, entries, batch = dirs[dirname]
        identity = EXPECTED_IDENTITIES[key]
        candidates = [r for r in entries if r[0] == identity]
        if len(candidates) != 1:
            raise ValueError("Missing or repeated declared intent")
        _, request_sha, state, raw_sha, audit_sha = candidates[0]
        if state != expected_state or not audit_sha:
            raise ValueError("Original ledger state differs")
        payload = payloads[key]
        if request_sha != sha(encoded(payload)):
            raise ValueError("Original request differs from sealed input")
        ready = records.get(audit_sha)
        if not isinstance(ready, dict) or ready.get('kind') != 'readiness_response' or ready.get('reason') != expected_reason:
            raise ValueError("Original readiness reason differs")
        if ready.get('request_sha256') != request_sha or ready.get('raw_sha256') != raw_sha:
            raise ValueError("Readiness receipt/ledger binding mismatch")
        raw_inner_or_envelope = bytes.fromhex(ready['raw_hex'])
        if sha(raw_inner_or_envelope) != raw_sha:
            raise ValueError("Original readiness raw hash differs")
        if node == 637:
            _, provider = find_one(records, kind='canary_provider_response')
            provider_id = next(k for k,v in records.items() if v is provider)
        else:
            context_kind = 'remaining_request' if dirname == 'gapgpt_remaining_pilot_v1' else 'outstanding_request'
            _, context = find_one(records, kind=context_kind, identity=identity)
            if context.get('request_sha256', context.get('payload_sha256')) != request_sha:
                raise ValueError("Request context hash differs")
            if context.get('wire_sha256') != sha(prior.wire_for(payload)):
                raise ValueError("Outbound wire digest differs from sealed wire")
            context_digest = sha(canonical(context))
            matching = [(k,v) for k,v in records.items() if isinstance(v,dict)
                        and v.get('kind') == 'canary_provider_response' and v.get('context_sha256') == context_digest]
            if len(matching) != 1:
                raise ValueError("Response context not uniquely bound")
            provider_id, provider = matching[0]
        raw = bytes.fromhex(provider['raw_hex'])
        if (provider.get('http_status') != 200 or provider.get('body_complete') is not True
                or provider.get('secret_echo_redacted') is not False
                or provider.get('original_response_sha256') != sha(raw)
                or provider.get('persisted_response_sha256') != sha(raw)):
            raise ValueError("Provider response absent, redacted or hash mismatch")
        env = strict_json(raw)
        if (env.get('model') not in ALLOWED_MODELS or type(env.get('choices')) is not list
                or len(env['choices']) != 1 or env['choices'][0].get('finish_reason') != 'stop'):
            raise ValueError("Unexpected provider identity/finish state")
        content = env['choices'][0]['message']['content']
        if type(content) is not str:
            raise ValueError("Missing text completion")
        value = strict_json(content)
        assert_readiness_raw_binding(expected_reason, raw_inner_or_envelope, raw, content)
        try:
            assessed = validate_result(value, payload['target']['text'])
            l1, fail_code = 'PASS', None
        except EvidenceError as exc:
            assessed = None
            l1, fail_code = 'FAIL', exc.code
        if node == 637 and l1 != 'PASS' or (node,phase) in ((1243,'blind'),(130,'blind'),(682,'blind'),(2396,'blind')) and l1 != 'PASS':
            raise ValueError("Expected blind diagnostic pass missing")
        if key in ((653,'blind'),(1243,'compare'),(130,'compare')) and fail_code != 'L1_QUOTE_NOT_FOUND':
            raise ValueError("Expected genuine L1 rejection changed")
        if state == 'COMPLETED' and l1 != 'PASS':
            raise ValueError("Completed ledger incompatible with current L1")
        if type(value) is not dict or type(value.get('abstain')) is not bool:
            raise ValueError("Unexpected parsed response")
        row = {'node':node,'phase':phase,'original_ledger_state':state,'original_reason':expected_reason,
               'original_readiness_sha256':audit_sha,'request_sha256':request_sha,
               'provider_receipt_sha256':provider_id,'provider_response_sha256':sha(raw),
               'provider_reported_model':env['model'],'http_status':200,'json_valid':True,
               'replayed_l1':l1,'replayed_l1_failure_code':fail_code,'abstain':value['abstain'],
               'evidence_count':len(value.get('evidence',[]))}
        rows.append(row)
        private[key] = {'payload':payload, 'value':value, 'row':row,
                        'quote_diagnostics':[diagnostic_kind(payload['target']['text'],q,quote_for_matching)
                                             for q in value.get('evidence',[])]}
    # Compare against the expected scientific outcomes; fail closed, never silently revise.
    if any(private[(n,'blind')]['value']['abstain'] != (n in (637,2396)) for n in NODES):
        raise ValueError("Blind abstention distribution differs")
    if len([r for r in rows if r['phase']=='compare']) != 2:
        raise ValueError("Comparison tally differs")
    if (private[(653,'blind')]['quote_diagnostics'].count('EXACT_AFTER_APPROVED_WRAPPER') != 1
            or len(private[(653,'blind')]['quote_diagnostics']) != 2):
        raise ValueError('653 exact-evidence diagnostic differs')
    if private[(653,'blind')]['quote_diagnostics'].count('INITIAL_CHARACTER_CASE_ONLY') != 1:
        raise ValueError("653 case-only diagnostic differs")
    if (private[(130,'compare')]['quote_diagnostics'].count('EXACT_AFTER_APPROVED_WRAPPER') != 1
            or len(private[(130,'compare')]['quote_diagnostics']) != 2):
        raise ValueError('130 comparison exact-evidence diagnostic differs')
    if private[(130,'compare')]['quote_diagnostics'].count('INITIAL_CHARACTER_CASE_ONLY') != 1:
        raise ValueError("130 comparison case-only diagnostic differs")
    if (len(private[(1243,'compare')]['quote_diagnostics']) != 2
            or any(d != 'NON_EXACT_OTHER' for d in private[(1243,'compare')]['quote_diagnostics'])):
        raise ValueError("1243 comparison diagnostics differ")
    totals = {'prompt_tokens':0,'completion_tokens':0,'reasoning_tokens':0}
    usage_present = 0
    for obj in private.values():
        provider = dirs[ORIGINAL[obj['row']['node'],obj['row']['phase']][0]][0][obj['row']['provider_receipt_sha256']]
        env = strict_json(bytes.fromhex(provider['raw_hex']))
        u = env.get('usage')
        if type(u) is not dict or type(u.get('prompt_tokens')) is not int or type(u.get('completion_tokens')) is not int:
            raise ValueError("Provider usage missing; cannot publish complete totals")
        p,c = u['prompt_tokens'],u['completion_tokens']
        if p < 0 or c < 0:
            raise ValueError("Negative provider token usage")
        usage_present += 1
        totals['prompt_tokens'] += p; totals['completion_tokens'] += c
        details = u.get('completion_tokens_details') or {}
        if not isinstance(details,dict):
            raise ValueError("Unsupported completion details")
        reasoning = details.get('reasoning_tokens',0)
        if type(reasoning) is not int or reasoning < 0:
            raise ValueError("Invalid reasoning tokens")
        totals['reasoning_tokens'] += reasoning
    if usage_present != 8:
        raise ValueError("Usage coverage incomplete")
    from decimal import Decimal
    estimate = (Decimal(totals['prompt_tokens'])*Decimal('0.10') +
                Decimal(totals['completion_tokens'])*Decimal('0.50')) / Decimal(1_000_000)
    return rows, private, totals, str(estimate)


def make_private_outputs(root, rows, private, totals, estimate):
    from llmgnn_sara.sara3.audit import PrivateAudit, _restrict_windows, _private_windows
    target = root / '.local_artifacts/sara3_feasibility_closeout_v1'
    if target.exists() or target.is_symlink():
        raise ValueError('Closeout already exists; no regeneration or overwrite')
    # Save initial verified data before touching protected output folders.
    report = public_report(rows, estimated_cost=estimate, usage=totals)
    parent = PrivateAudit(target)
    admin = PrivateAudit(target / 'admin')
    reviewers = {r: PrivateAudit(target / ('reviewer_' + r)) for r in ('A','B')}
    mapping = []
    for node in HUMAN_NODES:
        item = private[node,'blind']
        if item['row']['replayed_l1'] != 'PASS' or item['value']['abstain']:
            raise ValueError('Not eligible for L2')
        target_text = item['payload']['target']['text']
        atlas = item['payload']['class_atlas']
        index = item['value']['class_index']
        if type(index) is not int or not 0 <= index < len(atlas):
            raise ValueError('Invalid proposed class')
        from llmgnn_sara.sara3.evidence import quote_for_matching
        exact = [quote_for_matching(q) for q in item['value']['evidence']]
        if not exact or any(q not in target_text for q in exact):
            raise ValueError('Human case not source-exact')
        for reviewer in ('A','B'):
            case_id = secrets.token_hex(12)
            case = {
                'schema':'sara3.l2.blinded_case.v1', 'reviewer_case_id':case_id,
                'instructions_fa':[
                    'این ارزیابی باید مستقل باشد؛ پاسخ داور دیگر را نبینید و درباره آن گفتگو نکنید.',
                    'فقط متن مقاله، کلاس پیشنهادی و عبارات نقل‌شده را از نظر پشتیبانی معنایی بررسی کنید.',
                    'وجود لفظی نقل‌قول کافی نیست: آیا واقعاً موضوع اصلی مقاله این کلاس است؟',
                    'برای هر نقل‌قول و جمع‌بندی نهایی می‌توانید «نامطمئن» انتخاب کنید.',
                    'هیچ برچسب GT یا پیش‌بینی تاریخی در این بسته وجود ندارد.'
                ],
                'target_text':target_text,
                'proposed_class':{'class_index':index,'name':atlas[index]['name'],
                                  'definition':atlas[index]['definition']},
                'evidence_exact_target_excerpts':exact,
            }
            saved = reviewers[reviewer].write({'kind':'blinded_l2_case','case':case})
            mapping.append({'node':node,'reviewer':reviewer,'reviewer_case_id':case_id,
                            'case_receipt_sha256':saved,
                            'source_request_sha256':item['row']['request_sha256'],
                            'source_provider_receipt_sha256':item['row']['provider_receipt_sha256'],
                            'original_state':item['row']['original_ledger_state'],
                            'original_reason':item['row']['original_reason'],
                            'l1_replay':'PASS',
                            'l1_provenance':'ORIGINAL_PASS' if node == 682 else 'POST_OBSERVATION_DIAGNOSTIC_PASS',
                            'human_l2_status':'NOT_ASSESSED','accepted_label':None})
            template = make_response_form(case_id,len(exact))
            reviewers[reviewer].write({'kind':'blank_human_response_form','form':template})
    admin.write({'kind':'administrator_manifest',
                 'schema':SCHEMA,
                 'cases':mapping,'all_original_and_replayed_phase_outcomes':rows,
                 'usage':totals,'provisional_estimate_usd':estimate,
                 'original_labels_accepted':None,'l2_status':'NOT_ASSESSED'})
    admin.write({'kind':'scientific_closeout_report','report_fa':report})
    secure_new_file(target/'admin'/'FEASIBILITY_CLOSEOUT_FA.md',
                    report.encode('utf-8'),_restrict_windows,_private_windows,admin.sid)
    # README carries only non-sensitive instructions; secure permissions anyway.
    readme = ('SARA-3 blinded L2 review: share ONLY the files from your own reviewer directory.\n'
              'Never share admin directory or the whole parent folder.\n'
              'Each case receipt has kind=blinded_l2_case; each blank response form has kind=blank_human_response_form.\n'
              'Fill the form independently and return it privately to the administrator; do not modify receipt files.\n'
              'No evidence has been semantically approved. No label has been accepted.\n')
    secure_new_file(target/'INSTRUCTIONS.txt',readme.encode(),_restrict_windows,_private_windows,admin.sid)
    return target, report


def secure_new_file(path, blob, restrict, check, sid):
    fd = os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(blob); stream.flush(); os.fsync(stream.fileno())
    if os.name == 'nt':
        restrict(path,sid); check(path,sid)
    elif (path.stat().st_mode & 0o777) != 0o600:
        raise ValueError('Failed to restrict private file')


def main():
    root = Path(__file__).resolve().parent
    if not (root/'src/llmgnn_sara').is_dir() or not (root/'.git').exists():
        raise ValueError('Place this script at the root of the existing llm-gnn checkout')
    if str(root/'src') not in sys.path:
        sys.path.insert(0,str(root/'src'))
    rows, private, totals, estimate = load_verified(root)
    path, report = make_private_outputs(root,rows,private,totals,estimate)
    # Do not print raw evidence, target texts, class, user identities or private receipts.
    print(json.dumps({'state':'CLOSEOUT_CREATED','verified_original_intents':len(rows),
                      'blind_responses':6,'comparison_attempts':2,
                      'l2_independent_review_cases':6,'human_l2_status':'NOT_ASSESSED',
                      'private_output_directory':str(path.relative_to(root)),
                      'reported_usage_tokens':totals,'provisional_cost_usd':estimate},indent=2))


if __name__=='__main__':
    try:
        main()
    except (OSError,ValueError,TypeError,KeyError,IndexError,sqlite3.Error,ImportError) as exc:
        # Deliberately report only error type and safe reason class, not exception text.
        print(json.dumps({'state':'BLOCKED_NO_HISTORICAL_FILES_CHANGED',
                          'error_type':type(exc).__name__,
                          'note':'Inspect locally; do not rerun any API pilot. No raw data printed.'}))
        raise SystemExit(1)
