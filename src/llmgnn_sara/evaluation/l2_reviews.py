"""Private offline human-review packets, intake and comparison; no adjudication."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re

from .l2_benchmark import (BENCHMARK_SHA256, DIMENSIONS, RUBRIC_VERSION, _judgment,
                           materialize_case, validate_records)
from ..io.frozen import read_pinned_json, reject_gt, require
from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.inputs import canonical_bytes

PACKET_VERSION = "sara.l2.blinded_packet.v1"
REVIEW_VERSION = "sara.l2.human_review.v1"
SESSION_VERSION = "sara.l2.review_session.v1"
SCOPE = "DEVELOPMENT_ONLY_NOT_HOLDOUT"
DECLARATIONS = ("human_reviewer", "not_case_author", "no_author_judgments_seen",
                "no_other_review_seen", "no_gt_or_correctness_used", "no_llm_assistance")
RUBRIC = {
    "version": RUBRIC_VERSION,
    "dimensions": dict(zip(DIMENSIONS, (
        "Does the interpretation concern the primary research question or contribution?",
        "Does the quotation in context warrant the associated claim without adding unstated conclusions?",
        "Is material counter-evidence absent for this narrow claim or explicitly resolved?",
        "Does the interpretation distinguish the research aim from auxiliary components or techniques?"))),
    "outcomes": {
        "SUPPORTED": "Cited context warrants the narrow assessment; not proof of a node class.",
        "UNSUPPORTED": "An interpretation is unwarranted or contradicted; cite the specific failure.",
        "AMBIGUOUS": "Review performed, but multiple readings or incomplete context prevent resolution.",
        "NOT_ASSESSED": "No semantic assessment recorded; not an ambiguous or negative judgment."},
    "instructions": "Read the complete supplied article text and controlled proposal. Cite evidence IDs in each assessed judgment. Record overall judgment yourself; no aggregation rule applies. Do not consult author opinions, other reviews, GT/correctness diagnostics or an LLM."
}


def _digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _pseudonym(value):
    return type(value) is str and re.fullmatch(r"[a-z][a-z0-9-]{1,31}", value) is not None


def make_packet(case, text, case_id, reviewer):
    """Explicit allowlist: do not copy author reviews, descriptive IDs or votes."""
    require(_pseudonym(reviewer), "Invalid reviewer pseudonym")
    data = materialize_case(case, text)
    refs = {e["evidence_id"]: f"e{i+1:02d}" for i, e in enumerate(case["excerpts"])}
    evidence = [{"evidence_id": refs[e["evidence_id"]], "source_id": "target.text",
                 "quote": data["quotes"][e["evidence_id"]], "quote_sha256": e["quote_sha256"]}
                for e in case["excerpts"]]
    proposal = {"primary_topic": data["response"]["primary_topic"]}
    for group in ("supporting_evidence", "counter_evidence"):
        proposal[group] = [{"evidence_ref": refs[i["quote_ref"]], "claim": i["claim"]}
                           for i in case["rich_response_template"][group]]
    return json.loads(canonical_bytes({"schema_version": PACKET_VERSION, "case_id": case_id,
        "assigned_reviewer": reviewer, "scope": SCOPE, "rubric": RUBRIC,
        "article": {"source_id": "target.text", "text": text, "sha256": case["target_text_sha256"]},
        "evidence": evidence, "proposal": proposal}))


def blank_review(packet, packet_sha256):
    empty = lambda: {"outcome": None, "rationale": "", "evidence_refs": []}
    return {"schema_version": REVIEW_VERSION, "case_id": packet["case_id"],
            "packet_sha256": packet_sha256, "reviewer": packet["assigned_reviewer"],
            "scope": SCOPE, "rubric_version": RUBRIC_VERSION, "reviewed_at_utc": None,
            "declarations": {k: None for k in DECLARATIONS},
            "assessments": {k: empty() for k in DIMENSIONS}, "overall": empty()}


def prepare_reviews(benchmark_path, frozen_root, authentic_root, output, reviewers):
    benchmark = read_pinned_json(benchmark_path, BENCHMARK_SHA256)
    inputs = load_project_inputs(frozen_root, authentic_root)
    texts = {p.node_id: p.text for p in inputs.pairs}
    validate_records(benchmark, texts)
    require(type(reviewers) in (tuple, list) and len(reviewers) == 2
            and all(_pseudonym(r) for r in reviewers) and len(set(reviewers)) == 2,
            "Two distinct lowercase reviewer pseudonyms required")
    authors = {c["author_id"] for c in benchmark["cases"]}
    require(not set(reviewers) & authors, "Reviewer cannot be a case author")
    root = Path(output)
    require(not root.exists(), "Review session already exists; never overwrite")
    # Prepare and validate all source material before creating private output.
    planned = []
    for i, case in enumerate(sorted(benchmark["cases"], key=lambda c: _digest(c["case_id"]))):
        identity = f"case-{i+1:03d}"
        planned.append((case, identity, {r: make_packet(case, texts[case["node_id"]], identity, r) for r in reviewers}))
    PrivateAudit(root)
    coordinator = PrivateAudit(root / "coordinator")
    session = {"schema_version": SESSION_VERSION, "scope": SCOPE, "benchmark_sha256": BENCHMARK_SHA256,
               "rubric_version": RUBRIC_VERSION, "reviewers": list(reviewers), "cases": []}
    for reviewer in reviewers:
        PrivateAudit(root / "working" / reviewer)
    for case, identity, packets in planned:
        entry = {"case_id": identity, "source_case_id": case["case_id"], "author_id": case["author_id"],
                 "packets": {}, "blank_forms": {}}
        for reviewer, packet in packets.items():
            digest = PrivateAudit(root / "packets" / reviewer).write(packet)
            form = blank_review(packet, digest)
            entry["packets"][reviewer] = digest
            entry["blank_forms"][reviewer] = PrivateAudit(root / "forms" / reviewer).write(form)
            # Editable copies only; immutable originals retain their content hashes.
            for suffix, value in (("packet", packet), ("review", form)):
                path = root / "working" / reviewer / f"{identity}.{suffix}.json"
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream: stream.write(canonical_bytes(value))
        session["cases"].append(entry)
    for reviewer in reviewers:
        PrivateAudit(root / "reviews" / reviewer)
    digest = coordinator.write(session)
    return {"session_sha256": digest, "root": str(root.resolve()), "packet_count": 2*len(planned),
            "blank_form_count": 2*len(planned), "completed_human_reviews": 0,
            "scope": SCOPE, "independence": "REAL_HUMANS_REQUIRED_NOT_AUTHENTICATED"}


def _session(root, digest):
    session = PrivateAudit(Path(root)/"coordinator").read(digest)
    require(session.get("schema_version") == SESSION_VERSION and session.get("scope") == SCOPE
            and session.get("benchmark_sha256") == BENCHMARK_SHA256
            and session.get("rubric_version") == RUBRIC_VERSION, "Session scope/version differs")
    reviewers = session.get("reviewers")
    require(type(reviewers) is list and len(reviewers) == 2 and all(_pseudonym(r) for r in reviewers)
            and len(set(reviewers)) == 2, "Session reviewer roster differs")
    require(type(session.get("cases")) is list and len(session["cases"]) == 6
            and len({c["case_id"] for c in session["cases"]}) == 6, "Session case coverage differs")
    return session


def validate_review(record, packet, expected_packet_sha256, author_id):
    """Validate self-attestations/shape only; cannot authenticate a human identity."""
    reject_gt(record)
    expected = {"schema_version", "case_id", "packet_sha256", "reviewer", "scope", "rubric_version",
                "reviewed_at_utc", "declarations", "assessments", "overall"}
    require(type(record) is dict and set(record) == expected, "Review fields differ")
    require(record["schema_version"] == REVIEW_VERSION and record["scope"] == packet["scope"] == SCOPE
            and record["rubric_version"] == packet["rubric"]["version"] == RUBRIC_VERSION,
            "Review version/scope differs; holdout promotion forbidden")
    require(record["case_id"] == packet["case_id"] and record["packet_sha256"] == expected_packet_sha256
            and _digest(packet) == expected_packet_sha256, "Review packet/case binding differs")
    require(record["reviewer"] == packet["assigned_reviewer"] and _pseudonym(record["reviewer"])
            and record["reviewer"] != author_id, "Reviewer assignment/independence differs")
    declarations = record["declarations"]
    require(type(declarations) is dict and set(declarations) == set(DECLARATIONS)
            and all(v is True for v in declarations.values()), "Human independence declarations incomplete")
    stamp = record["reviewed_at_utc"]
    require(type(stamp) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp) is not None,
            "UTC review timestamp required")
    try:
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        require(False, "Invalid review timestamp")
    assessments = record["assessments"]
    require(type(assessments) is dict and set(assessments) == set(DIMENSIONS), "Four rubric assessments required")
    refs = {e["evidence_id"] for e in packet["evidence"]}
    for assessment in (*assessments.values(), record["overall"]): _judgment(assessment, refs)
    if record["overall"]["outcome"] == "NOT_ASSESSED":
        require(all(a["outcome"] == "NOT_ASSESSED" for a in assessments.values()), "Unassessed review contains assessed dimensions")
    return record


def _records(root, session):
    rows = {}
    for reviewer in session["reviewers"]:
        store = PrivateAudit(Path(root)/"reviews"/reviewer)
        for path in sorted(store.root.glob("*.json")):
            record = store.read(path.stem)
            require(type(record) is dict, "Malformed private review")
            case = next((c for c in session["cases"] if c["case_id"] == record.get("case_id")), None)
            require(case is not None, "Review case outside session")
            packet_hash = case["packets"][reviewer]
            packet = PrivateAudit(Path(root)/"packets"/reviewer).read(packet_hash)
            validate_review(record, packet, packet_hash, case["author_id"])
            require(record["reviewer"] == reviewer, "Review stored under another reviewer")
            key = case["case_id"], reviewer
            require(key not in rows, "Conflicting duplicate review; no automatic selection")
            rows[key] = record
    return rows


def import_review(root, session_sha256, review_path, review_sha256):
    session = _session(root, session_sha256)
    record = read_pinned_json(review_path, review_sha256)
    require(type(record) is dict and record.get("reviewer") in session["reviewers"], "Reviewer outside session")
    reviewer = record["reviewer"]
    case = next((c for c in session["cases"] if c["case_id"] == record.get("case_id")), None)
    require(case is not None, "Case outside session")
    packet_hash = case["packets"][reviewer]
    packet = PrivateAudit(Path(root)/"packets"/reviewer).read(packet_hash)
    validate_review(record, packet, packet_hash, case["author_id"])
    existing = _records(root, session).get((case["case_id"], reviewer))
    require(existing is None or existing == record, "Conflicting review; preserve original")
    return PrivateAudit(Path(root)/"reviews"/reviewer).write(record)


def _agreement(a, b):
    if a is None or b is None: return "MISSING_REVIEW"
    if a == b == "NOT_ASSESSED": return "BOTH_NOT_ASSESSED"
    if "NOT_ASSESSED" in (a, b): return "INCOMPLETE_ASSESSMENT"
    return "AGREEMENT" if a == b else "DISAGREEMENT"


def compare_reviews(root, session_sha256):
    session = _session(root, session_sha256)
    records = _records(root, session)
    rows = []
    for case in session["cases"]:
        pair = [records.get((case["case_id"], r)) for r in session["reviewers"]]
        overall = [r["overall"]["outcome"] if r else None for r in pair]
        rows.append({"case_id": case["case_id"], "missing_reviewers": [name for name, r in zip(session["reviewers"], pair) if r is None],
                     "overall_outcomes": overall, "overall_comparison": _agreement(*overall),
                     "dimension_comparison": {d: _agreement(*(r["assessments"][d]["outcome"] if r else None for r in pair)) for d in DIMENSIONS}})
    return {"scope": SCOPE, "reviewers": session["reviewers"], "cases": rows,
            "human_self_attested_records": len(records), "missing_records": 12-len(records),
            "identity_and_independence": "SELF_ATTESTED_NOT_AUTHENTICATED", "adjudication": "NOT_PERFORMED",
            "gold_standard": False, "runtime_l2_status": "NOT_ASSESSED", "training_use": "FORBIDDEN"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    for name in ("benchmark", "frozen-root", "authentic-root", "output"): prepare.add_argument("--"+name, required=True)
    prepare.add_argument("--reviewers", nargs=2, required=True)
    for name in ("compare", "import"):
        command = sub.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--session-sha256", required=True)
        if name == "import":
            command.add_argument("--review-file", required=True)
            command.add_argument("--review-sha256", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_reviews(args.benchmark, args.frozen_root, args.authentic_root, args.output, args.reviewers)
    elif args.command == "compare": result = compare_reviews(args.root, args.session_sha256)
    else: result = {"imported_review_sha256": import_review(args.root, args.session_sha256, args.review_file, args.review_sha256)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
