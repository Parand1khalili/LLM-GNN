"""Isolated GT-free benchmark admission; never scores semantics or approves labels."""
import argparse
from collections import Counter
import hashlib
import json

from ..io.frozen import read_pinned_json, reject_gt, require
from ..io.project import load_project_inputs
from ..sara3.evidence import validate_claims
from ..sara3.rich_evidence import target_source, validate_rich_result

BENCHMARK_SHA256 = "d6f84007bd79da2cf389976e8410f2a4f9822225ae001ff88b11a252ac3451b2"
RUBRIC_VERSION = "sara.l2.rubric.v1"
OUTCOMES = frozenset({"SUPPORTED", "UNSUPPORTED", "AMBIGUOUS", "NOT_ASSESSED"})
DIMENSIONS = ("primary_topic_relevance", "quote_claim_support",
              "counter_evidence_resolution", "topic_method_separation")


def _text(value):
    return type(value) is str and bool(value.strip()) and len(value) <= 4000


def _judgment(record, known_refs):
    require(type(record) is dict and set(record) == {"outcome", "rationale", "evidence_refs"},
            "Invalid rubric judgment fields")
    require(type(record["outcome"]) is str and record["outcome"] in OUTCOMES
            and _text(record["rationale"]), "Invalid rubric outcome/rationale")
    refs = record["evidence_refs"]
    require(type(refs) is list and all(type(r) is str for r in refs)
            and len(refs) == len(set(refs)) and set(refs) <= known_refs, "Unknown/duplicate reviewer evidence reference")
    require(record["outcome"] == "NOT_ASSESSED" or bool(refs), "Assessed judgment requires cited evidence")


def materialize_case(case, text):
    """Resolve pinned excerpts for authorized offline review; no semantic decision."""
    reject_gt(case)
    require(type(text) is str and bool(text.strip()), "Invalid source text")
    require(hashlib.sha256(text.encode()).hexdigest() == case["target_text_sha256"], "Target text hash differs")
    excerpts = case["excerpts"]
    require(type(excerpts) is list and 1 <= len(excerpts) <= 4, "Invalid benchmark excerpt count")
    quotes, claims = {}, []
    source = target_source(text)
    for entry in excerpts:
        require(type(entry) is dict and set(entry) == {"evidence_id", "source_id", "start", "end", "quote_sha256"},
                "Invalid benchmark excerpt fields")
        identity = entry["evidence_id"]
        require(_text(identity) and identity not in quotes and entry["source_id"] == source.source_id,
                "Unknown source or duplicate excerpt ID")
        a, b = entry["start"], entry["end"]
        require(type(a) is int and type(b) is int and 0 <= a < b <= len(text), "Invalid excerpt bounds")
        quote = text[a:b]
        require(hashlib.sha256(quote.encode()).hexdigest() == entry["quote_sha256"], "Excerpt hash differs")
        quotes[identity] = quote
        claims.append({"source_id": source.source_id, "field": source.field,
                       "source_sha256": source.sha256, "quote": quote})
    validate_claims(claims, (source,))
    response = json.loads(json.dumps(case["rich_response_template"], allow_nan=False))
    require(type(response) is dict, "Invalid rich response template")
    for group in ("supporting_evidence", "counter_evidence"):
        require(type(response.get(group)) is list, "Invalid template evidence list")
        for item in response[group]:
            require(type(item) is dict and set(item) == {"source_id", "quote_ref", "claim"}, "Invalid template evidence fields")
            require(item["source_id"] == source.source_id and type(item["quote_ref"]) is str
                    and item["quote_ref"] in quotes, "Template source/reference differs")
            item["quote"] = quotes[item.pop("quote_ref")]
    validated = validate_rich_result(response, (source,))
    require(validated["l2_status"] == "NOT_ASSESSED", "Unexpected runtime semantic approval")
    return {"source_text": text, "quotes": quotes, "response": response, "l1_status": validated["l1_status"]}


def validate_records(benchmark, texts):
    """Validate record structure and provenance, NOT the author's semantic opinions."""
    reject_gt(benchmark)
    require(type(benchmark) is dict and set(benchmark) == {"schema", "rubric_version", "status", "selection",
            "training_use", "future_holdout_eligible", "cases"}, "Invalid benchmark fields")
    require(benchmark["schema"] == "sara.l2.development_benchmark.v1"
            and benchmark["rubric_version"] == RUBRIC_VERSION
            and benchmark["status"] == "ILLUSTRATIVE_NOT_GOLD_INDEPENDENT_REVIEW_PENDING"
            and _text(benchmark["selection"]) and benchmark["training_use"] == "FORBIDDEN"
            and benchmark["future_holdout_eligible"] is False, "Benchmark scope/version differs")
    cases = benchmark["cases"]
    require(type(cases) is list and bool(cases), "Empty benchmark")
    seen, outcomes, nodes = set(), Counter(), set()
    for case in cases:
        require(type(case) is dict and set(case) == {"case_id", "node_id", "author_id", "usage",
            "future_holdout_eligible", "target_text_sha256", "excerpts", "rich_response_template", "review"},
            "Invalid benchmark case fields")
        identity, node = case["case_id"], case["node_id"]
        require(_text(identity) and identity not in seen, "Duplicate/invalid case ID")
        require(type(node) is int and node in texts, "Node outside admitted cohort")
        require(_text(case["author_id"]) and case["usage"] == "DEVELOPMENT_FIXTURE_NOT_HOLDOUT"
                and case["future_holdout_eligible"] is False, "Fixture/holdout separation violated")
        materialized = materialize_case(case, texts[node])
        review = case["review"]
        require(type(review) is dict and set(review) == {"rubric_version", "reviewer_id", "kind",
                "independently_reviewed", "basis", "dimensions", "overall"}, "Invalid reviewer provenance fields")
        require(review["rubric_version"] == RUBRIC_VERSION and review["reviewer_id"] == case["author_id"]
                and review["kind"] == "ILLUSTRATIVE" and review["independently_reviewed"] is False
                and review["basis"] == "AUTHOR_TEXT_READING_NO_SCORING_HEURISTIC_OR_JUDGE_TEST",
                "Independent review evidence not provided; illustrative author provenance required")
        require(type(review["dimensions"]) is dict and set(review["dimensions"]) == set(DIMENSIONS),
                "Incomplete rubric dimensions")
        refs = set(materialized["quotes"])
        for record in (*review["dimensions"].values(), review["overall"]): _judgment(record, refs)
        if review["overall"]["outcome"] == "NOT_ASSESSED":
            require(all(r["outcome"] == "NOT_ASSESSED" for r in review["dimensions"].values()),
                    "Unassessed record contains assessed dimensions")
        outcomes[review["overall"]["outcome"]] += 1
        seen.add(identity); nodes.add(node)
    return {"status": "PASS_STRUCTURE_AND_L1_ONLY", "cases": len(cases), "nodes": sorted(nodes),
            "illustrative_outcome_counts": dict(sorted(outcomes.items())), "independently_reviewed": 0,
            "gold_standard": False, "semantic_accuracy_measured": False, "runtime_l2_status": "NOT_ASSESSED",
            "future_holdout_eligible": False, "training_use": "FORBIDDEN"}


def validate_benchmark(path, frozen_root, authentic_root):
    benchmark = read_pinned_json(path, BENCHMARK_SHA256)
    inputs = load_project_inputs(frozen_root, authentic_root)
    report = validate_records(benchmark, {p.node_id: p.text for p in inputs.pairs})
    return {**report, "benchmark_sha256": BENCHMARK_SHA256, "rubric_version": RUBRIC_VERSION,
            "source_sha256": dict(inputs.provenance), "provider_calls": 0, "training_runs": 0, "GT_accessed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--authentic-root", required=True)
    args = parser.parse_args()
    print(json.dumps(validate_benchmark(args.benchmark, args.frozen_root, args.authentic_root), indent=2))


if __name__ == "__main__": main()
