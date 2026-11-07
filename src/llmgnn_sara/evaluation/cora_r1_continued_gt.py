"""Verify real R1-v1 continuation receipts GT-free, then privately score GT.

Never resumes, calls the provider, mutates a journal or feeds labels to
inference. Rejection L1_QUOTE_NOT_FOUND is intentionally preserved.
"""
import argparse
import json
from pathlib import Path
import sys

from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.gateway_continuation import identity, journal_rows, replay
from ..sara3.gateway_r1_continuation import (
    AMENDMENT_VERSION, OVERLAY, REJECT_CODE, VERSION as GATEWAY_VERSION,
    BUDGET, COHORT, ORIGINAL_CALLS, ORIGINAL_COMPLETED, MAX_NEW,
    _read_sha, _root, preflight)
from ..sara3.gapgpt_live import contract_from_dict, wire_for
from ..sara3.rich_evidence import rich_verifier_input_v2
from ..sara3.experiment import digest
from ..sara3.gateway_run import gateway_context
from .cora_gt_shadow import (
    EvaluationStageError, GRAPH_SHA256, _expected_graph_names,
    _labels_from_original_graph, _require)
from .cora_r1_real_gt import analyze

VERSION = "sara.evaluation.cora140.r1_v1_continued_gt.v1"


def run(frozen_root, authentic_root, original_root, config_file,
        continuation_summary_sha, graph_file, audit_root):
    stage = "OWNER_PRIVATE_PATH_PREFLIGHT"
    try:
        root, output = _root(original_root), _root(audit_root)
        graph = Path(graph_file).resolve(strict=True)
        cfg_path = Path(config_file).resolve(strict=True)
        _require(output.parent.is_dir() and root != output
                 and root not in output.parents and output not in root.parents
                 and cfg_path.is_file() and cfg_path.stat().st_size <= 16384
                 and output != graph and graph not in output.parents)
        cfg = contract_from_dict(json.loads(cfg_path.read_text(encoding="utf-8")))
        inputs = load_project_inputs(frozen_root, authentic_root)
        stage = "R1_ORIGINAL_PRE_GT_RECONCILIATION"
        checked = preflight(inputs, root, config=cfg, fake=False)
        amendment = checked["amendment_template"]
        _, context = gateway_context(inputs, "r1_v1", BUDGET,
                                     "sensitivity", cfg, fake=False)
        context_sha = digest(context)
        selected = list(amendment["never_dispatched_blind_ids"])
        _require(len(selected) == 7 and
                 amendment["original_reject_code"] == REJECT_CODE)
        stage = "R1_OVERLAY_REPLAY_AND_TRUST"
        overlay = root / OVERLAY
        journal = overlay / "journal"
        summary = _read_sha(journal, continuation_summary_sha)
        report_sha = summary.get("private_combined_report_sha256")
        report = _read_sha(journal, report_sha)
        run_data = report.get("run")
        _require(type(run_data) is dict and
                 summary.get("schema") == GATEWAY_VERSION and
                 summary.get("status") == "CONTINUED_PRESERVING_REJECTED_COMPARISON" and
                 summary.get("source_original_summary_sha256") ==
                     amendment["original_summary_sha256"] and
                 summary.get("source_original_report_sha256") ==
                     amendment["original_report_sha256"] and
                 summary.get("source_original_journal_rows_sha256") ==
                     amendment["original_journal_rows_sha256"] and
                 summary.get("gateway_context_sha256") == context_sha and
                 summary.get("amendment_sha256") == digest(amendment) and
                 summary.get("original_intents") == ORIGINAL_CALLS and
                 summary.get("original_completed") == ORIGINAL_COMPLETED and
                 summary.get("original_rejected") == 1 and
                 summary.get("read_only_original_journal") is True and
                 summary.get("GT_accessed") is False and
                 summary.get("training_runs") == 0 and
                 summary.get("training_admission") is False and
                 report.get("schema") == GATEWAY_VERSION and
                 report.get("kind") == "gapgpt_r1_v1_continuation_private_report" and
                 report.get("amendment_sha256") == digest(amendment) and
                 report.get("original_summary_sha256") ==
                     amendment["original_summary_sha256"] and
                 report.get("original_report_sha256") ==
                     amendment["original_report_sha256"] and
                 report.get("original_journal_rows_sha256") ==
                     amendment["original_journal_rows_sha256"] and
                 run_data.get("gateway_runner_version") == GATEWAY_VERSION and
                 run_data.get("router") == "r1_v1" and
                 run_data.get("review_budget") == BUDGET and
                 run_data.get("target_count") == COHORT and
                 run_data.get("gateway_context_sha256") == context_sha and
                 run_data.get("source_hashes") == dict(inputs.provenance) and
                 run_data.get("data_kind") ==
                     "GAPGPT_LIVE_R1_CONTINUED_RETAINING_REJECTED" and
                 run_data.get("GT_accessed") is False and
                 run_data.get("training_runs") == 0 and
                 len(run_data.get("decisions", [])) == COHORT)
        base, base_phases = journal_rows(root, context_sha, cfg["max_calls"])
        overlay_rows, overlay_phases = journal_rows(overlay, context_sha, cfg["max_calls"])
        _require(len(base) == ORIGINAL_CALLS and
                 len(overlay_rows) == summary["new_intents"] and
                 0 <= len(overlay_rows) <= MAX_NEW and
                 len(base) + len(overlay_rows) == summary["total_intents"] and
                 len(set(base) & set(overlay_rows)) == 0 and
                 len(set(base_phases) & set(overlay_phases)) == 0 and
                 summary["total_intents"] <= ORIGINAL_CALLS + MAX_NEW and
                 set(n for n, phase in overlay_phases) <= set(selected) and
                 all(row[1][3] == "COMPLETED" for row in overlay_phases.values()) and
                 set(n for n, phase in overlay_phases if phase == "blind") ==
                     set(selected) and
                 len(overlay_phases) == summary["new_state_counts"]["COMPLETED"] and
                 summary["new_state_counts"]["REJECTED"] == 0 and
                 summary["new_state_counts"]["UNCERTAIN"] == 0)
        audit = PrivateAudit(journal)
        pairs = {p.node_id: p for p in inputs.pairs}
        for node in selected:
            pair = pairs[node]
            bp = rich_verifier_input_v2(node, pair.text, pair.neighborhood)
            bw = wire_for(bp, cfg)
            bi = identity(context_sha, "blind", bp, bw, None)
            row = overlay_phases.get((node, "blind"))
            _require(row is not None)
            blind = replay(audit, row, bi, bp, bw, None, context_sha,
                           pair.text, cfg)
            if (node, "compare") not in overlay_phases:
                _require(blind["abstain"] is True)
                continue
            _require(blind["abstain"] is False)
            cp = rich_verifier_input_v2(
                node, pair.text, pair.neighborhood,
                candidates=tuple(sorted({pair.b1.class_index,
                                         pair.narrative_v0.class_index})),
                blind_class=blind["class_index"])
            cw = wire_for(cp, cfg)
            ci = identity(context_sha, "compare", cp, cw, digest(blind))
            replay(audit, overlay_phases[(node, "compare")], ci, cp, cw,
                   digest(blind), context_sha, pair.text, cfg)
        all_selected = list(gateway_context(
            inputs, "r1_v1", BUDGET, "sensitivity", cfg, fake=False)[0])
        _require(run_data.get("selected_node_ids") == all_selected
                 and run_data.get("provider_calls") == summary["total_intents"]
                 and summary["blinds_completed"] == BUDGET
                 and summary["comparisons_completed"] ==
                     20 + sum(p == "compare" for n, p in overlay_phases)
                 and sum(d.get("accepted") is True and
                         d.get("routed_for_review") is True
                         for d in run_data["decisions"]) == 0)
        stage = "PINNED_GRAPH_GT_ONLY"
        truth = _labels_from_original_graph(
            graph, _expected_graph_names(frozen_root))
        stage = "R1_CONTINUED_POST_HOC_SCORING"
        result = analyze(all_selected, run_data["decisions"], pairs, truth,
                         status="CONTINUED_PRESERVING_REJECTED_COMPARISON")
        result["source_original_summary_sha256"] = amendment["original_summary_sha256"]
        result["source_continuation_summary_sha256"] = continuation_summary_sha
        result["source_combined_report_sha256"] = report_sha
        result["source_graph_sha256"] = GRAPH_SHA256
        result["aggregate"]["real_live_attempts_total"] = summary["total_intents"]
        result["aggregate"]["new_live_dispatches"] = summary["new_dispatches"]
        result["aggregate"]["original_rejected_comparison_preserved"] = 1
        stage = "PRIVATE_OWNER_GT_AUDIT"
        private = PrivateAudit(output)
        sha = private.write(result)
        _require(private.read(sha) == result)
        return {"status": "R1_CONTINUED_GT_NODE_JOURNEY_VERIFIED_PRIVATE",
                "artifact_sha256": sha,
                "relative_path": sha + ".json",
                "aggregate": result["aggregate"]}
    except EvaluationStageError:
        raise
    except Exception:
        raise EvaluationStageError(stage) from None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("frozen-root", "authentic-root", "original-root",
                 "gateway-config", "graph-file", "audit-root"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--continuation-summary-sha256", required=True)
    args = p.parse_args(argv)
    try:
        value = run(args.frozen_root, args.authentic_root, args.original_root,
                    args.gateway_config, args.continuation_summary_sha256,
                    args.graph_file, args.audit_root)
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                         allow_nan=False))
        return 0
    except EvaluationStageError as error:
        print(json.dumps({"status": "FAIL_CLOSED", "stage": error.stage}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
