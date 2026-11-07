"""Fixed automatic evidence-first shadow score; no GT, review or training."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ..io.frozen import read_pinned_json
from .audit import PrivateAudit
from .correction_features import validate, require
from .experiment import digest
from . import weighted_arbitration_v2 as base

VERSION = "sara.arbitration.evidence.v3"
BASE_REPORT_SHA = "56e485e635ac915d07a0bb1b8849f5beb9017bd6f1ca9028192a64de335c0417"
# Prespecified engineering defaults, before scoring and before GT evaluation.
CONTRACT = {"version": VERSION, "weights": {"Q": 2, "T": 2, "P": 1, "N": 1, "A": -1, "C": -2, "U": -1},
            "candidate_threshold": 3, "third_class_threshold": 4,
            "require_each_phase_valid_support": True, "require_P_or_N": False,
            "missing_rule": "NULL_NEUTRAL_ZERO_CONTRIBUTION_NOT_OBSERVED_ABSENCE",
            "feature_definitions": "UNCHANGED_FROZEN_CORRECTION_FEATURES_V1_AND_WEIGHTED_V2",
            "optional_support_source_sha256": BASE_REPORT_SHA,
            "mode": "EXPERIMENTAL_SHADOW_NO_TRAINING_AUTHORIZATION"}


def decide(row, optional, cfg):
    # Reuse strict phase/type checks and the existing Q/T/A/C/U definitions.
    result = {**base.decide(row, optional, cfg), "policy_version": VERSION}
    if result["decision"] == "NO_VALID_AGENT_RESPONSE" or result["reason"] == "PHASE_CLASS_DISAGREEMENT":
        return result
    for phase in (row["blind"], row["compare"]):
        count, lengths = phase["support_count"], phase["quote_lengths"]
        if count is None or count == 0:
            return {**result, "decision": "NO_VALID_AGENT_RESPONSE", "label": row["narrative_class"],
                    "reason": "MISSING_L1_SUPPORT", "score": None}
        require(type(count) is int and count > 0 and type(lengths) is list and len(lengths) == count
                and all(type(n) is int and n > 0 for n in lengths))
    require(row["shared_support"] is None or row["shared_support"] <=
            min(row[p]["support_count"] for p in ("blind", "compare")))
    terms = result["components"]
    score = sum(CONTRACT["weights"][k] * (v if v is not None else 0) for k, v in terms.items())
    result.update(score=score, decision="KEEP_NARRATIVE", label=row["narrative_class"], reason="UNCHANGED")
    if result["agent_class"] == row["narrative_class"]: return result
    threshold = CONTRACT["third_class_threshold"] if result["third_class"] else CONTRACT["candidate_threshold"]
    if score < threshold: return {**result, "reason": "BELOW_EVIDENCE_THRESHOLD"}
    return {**result, "decision": "SWITCH_TO_AGENT", "label": result["agent_class"],
            "reason": "EXPERIMENTAL_EVIDENCE_SCORE_PASS"}


def score(table, baseline):
    validate(table)
    require(baseline["schema"] == base.VERSION and digest(baseline["config"]) == base.CONFIG_SHA
            and baseline["source_feature_sha256"] == base.FEATURE_SHA)
    indexed = {(r["router"], r["node_id"]): r for r in baseline["rows"]}
    require(len(indexed) == len(baseline["rows"]) == 74 and set(indexed) ==
            {(r["router"], r["node_id"]) for r in table["rows"]})
    rows = []
    for source in table["rows"]:
        prior = indexed[source["router"], source["node_id"]]
        optional = {k: prior["support"][k] for k in ("P", "N")}
        expected = base.decide(source, optional, baseline["config"])
        require(all(prior.get(k) == v for k, v in expected.items()))
        rows.append({"router": source["router"], "node_id": source["node_id"],
                     "narrative_class": source["narrative_class"], "optional_support": optional,
                     **decide(source, optional, baseline["config"])})
    return rows


def validate_report(report, table, baseline):
    require(report["schema"] == VERSION and report["contract"] == CONTRACT
            and report["rule_sha256"] == digest(CONTRACT)
            and report["source_feature_sha256"] == base.FEATURE_SHA
            and report["base_report_sha256"] == BASE_REPORT_SHA
            and report["training_admissions"] == 0 and report["rows"] == score(table, baseline))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("features", "base-report", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args(argv)
    try:
        table = read_pinned_json(args.features, base.FEATURE_SHA)
        baseline = read_pinned_json(args.base_report, BASE_REPORT_SHA)
        require(".local_artifacts" in args.output.absolute().parts)
        store = PrivateAudit(args.output)
        rule_sha = store.write(CONTRACT)  # Freeze before computing any V3 scores.
        report = {"schema": VERSION, "contract": CONTRACT, "rule_sha256": rule_sha,
                  "source_feature_sha256": base.FEATURE_SHA, "base_report_sha256": BASE_REPORT_SHA,
                  "rows": score(table, baseline), "training_admissions": 0}
        validate_report(report, table, baseline)
        sha = store.write(report); require(store.read(sha) == report)
        print(json.dumps({"status": "V3_GT_FREE_FROZEN", "rule_sha256": rule_sha, "report_sha256": sha,
                          "routers": {r: dict(Counter(v["decision"] for v in report["rows"] if v["router"] == r))
                                      for r in ("r0", "r1_v1")}}))
        return 0
    except Exception:
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
