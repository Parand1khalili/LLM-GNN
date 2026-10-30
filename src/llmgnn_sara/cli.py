"""One offline entry point; no provider, graph-pickle or training execution path."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import platform
import sys

from . import __version__


def doctor() -> dict:
    optional = {name: importlib.util.find_spec(name) is not None
                for name in ("torch", "torch_geometric", "tiktoken")}
    return {"status": "PASS", "scope": "standard_library_offline_runtime",
            "version": __version__, "python": platform.python_version(),
            "optional_dependencies": optional,
            "gcn_numeric_forward_available": optional["torch"] and optional["torch_geometric"],
            "provider_execution": "DISABLED", "training_execution": "DISABLED",
            "raw_response_recovery": "NOT_ESTABLISHED_BY_DOCTOR"}


def _inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--b1", type=Path, required=True)
    parser.add_argument("--narrative", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)


def _dataset(args):
    from .io.frozen import load_frozen
    return load_frozen(args.b1, args.narrative, args.selection)


def _pairs(dataset):
    from .sara2 import Annotation, Pair
    b1 = dataset.by_arm("b1")
    narrative = dataset.by_arm("narrative_v0")
    return tuple(Pair(Annotation(a.target_id, a.class_index, a.confidence_percent),
                      Annotation(b.target_id, b.class_index, b.confidence_percent))
                 for a, b in zip(b1, narrative))


def _plan(dataset, cohort, loss, accepted=None, arm="narrative_v0"):
    from .downstream import GCNConfig, PseudoLabel, gcn_plan
    # The five supplementary replacement targets are a frozen source property,
    # not a correctness-derived exclusion or a newly tuned cohort.
    excluded = tuple(p.target_id for p in dataset.by_arm("b1")
                     if p.samples[0].source_kind == "supplementary")
    records = dataset.by_arm(arm)
    if accepted is None:
        labels = tuple(PseudoLabel(p.target_id, p.class_index, p.confidence_percent)
                       for p in records if cohort != "primary" or p.target_id not in excluded)
    else:
        candidates = {}
        for p in dataset.predictions:
            candidates.setdefault(p.target_id, set()).add(p.class_index)
        converted = []
        for d in accepted:
            if type(d) is not dict or type(d.get("accepted")) is not bool:
                raise ValueError("Invalid arbitration decision")
            if not d["accepted"]:
                if d.get("training_class_index") is not None:
                    raise ValueError("Abstention cannot assign a training label")
                continue
            if (d.get("third_class_training_allowed") is not False
                    or d.get("third_class_proposal") is not None
                    or type(d.get("node_id")) is not int
                    or type(d.get("training_class_index")) is not int
                    or d["training_class_index"] not in candidates.get(d["node_id"], set())):
                raise ValueError("Unapproved third-class training label")
            if cohort != "primary" or d["node_id"] not in excluded:
                converted.append(PseudoLabel(d["node_id"], d["training_class_index"],
                                             d["label_confidence_percent"]))
        labels = tuple(converted)
        if not labels:
            return {"status": "BLOCKED_NO_ACCEPTED_LABELS", "train_count": 0,
                    "training_runs": 0, "GT_accessed": False}
    result = gcn_plan(dataset.target_ids, labels, cohort=cohort,
                      excluded_ids=excluded if cohort == "primary" else (),
                      config=GCNConfig(loss=loss), allow_abstention=accepted is not None)
    result["pseudo_label_origin"] = arm if accepted is None else "RECONSTRUCTED_SARA_OFFLINE"
    return result


def _baseline_plans(dataset, cohort, loss, arm):
    arms = ("b1", "narrative_v0") if arm == "both" else (arm,)
    return {name: _plan(dataset, cohort, loss, arm=name) for name in arms}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Offline dependencies and execution boundaries")
    replay = sub.add_parser("replay-frozen", help="Re-vote stored parsed samples; never raw parsing")
    _inputs(replay)
    sara = sub.add_parser("sara3-offline", help="GT-free offline policy/verifier decisions")
    sara.add_argument("--demo", action="store_true", help="Use explicitly synthetic cases")
    sara.add_argument("--b1", type=Path)
    sara.add_argument("--narrative", type=Path)
    sara.add_argument("--selection", type=Path)
    sara.add_argument("--budget", type=int, default=10)
    sara.add_argument("--router", choices=("r0", "semantic"), default="r0")
    for name in ("gcn-plan", "pipeline"):
        command = sub.add_parser(name, help="Frozen offline plan; training is disabled")
        _inputs(command)
        command.add_argument("--cohort", choices=("primary", "sensitivity"), default="sensitivity")
        command.add_argument("--loss", choices=("ce", "wce"), default="ce")
        command.add_argument("--arm", choices=("b1", "narrative_v0", "both"), default="both")
        if name == "pipeline":
            command.add_argument("--budget", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "replay-frozen":
            from .annotation.replay import replay_frozen
            result = replay_frozen(args.b1, args.narrative, args.selection)
        elif args.command == "sara3-offline":
            from .sara3 import offline_demo, run_offline
            if args.demo:
                if any((args.b1, args.narrative, args.selection)):
                    parser.error("--demo cannot be combined with historical artifact paths")
                result = offline_demo()
            else:
                if not all((args.b1, args.narrative, args.selection)):
                    parser.error("provide all frozen artifact paths, or explicitly use --demo")
                result = run_offline(_pairs(_dataset(args)), budget=args.budget, router=args.router)
        elif args.command == "gcn-plan":
            result = {"status": "PLANNED_NOT_TRAINED",
                      "by_arm": _baseline_plans(_dataset(args), args.cohort, args.loss, args.arm)}
        else:
            from .annotation.replay import replay_frozen
            from .sara3 import run_offline
            replay_result = replay_frozen(args.b1, args.narrative, args.selection)
            if replay_result.get("status") != "PASS":
                print(json.dumps({"status": "FAIL", "replay": replay_result,
                                  "extensions": "NOT_RUN_BASELINE_MISMATCH"}, allow_nan=False))
                return 1
            dataset = _dataset(args)
            pairs = _pairs(dataset)
            if args.cohort == "primary":
                excluded = {p.target_id for p in dataset.by_arm("b1")
                            if p.samples[0].source_kind == "supplementary"}
                pairs = tuple(pair for pair in pairs if pair.node_id not in excluded)
            decisions = run_offline(pairs, budget=args.budget, router="r0")
            result = {"scope": "FROZEN_PARSED_SAMPLES_AND_OFFLINE_EXTENSION",
                      "replay": replay_result,
                      "sara3": decisions,
                      "baseline_gcn_plans": _baseline_plans(dataset, args.cohort, args.loss, args.arm),
                      "sara_gcn_plan": _plan(dataset, args.cohort, args.loss,
                                              accepted=decisions["decisions"]),
                      "training_performed": False, "provider_calls": 0,
                      "GT_decoded": False}
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        failed = result.get("status") in ("FAIL", "MISMATCH")
        if args.command == "pipeline":
            failed = failed or result["replay"].get("status") != "PASS"
        return 1 if failed else 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        # Do not echo untrusted file contents, credentials or raw exception text.
        print(json.dumps({"status": "FAIL", "reason_type": type(error).__name__}), file=sys.stderr)
        return 1
