"""Matched plans from validated frozen annotations and conservative arbitration."""
def plan_from_frozen(dataset, cohort, loss, accepted=None, arm="narrative_v0"):
    from . import GCNConfig, PseudoLabel, gcn_plan
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


def baseline_plans(dataset, cohort, loss, arm):
    arms = ("b1", "narrative_v0") if arm == "both" else (arm,)
    return {name: plan_from_frozen(dataset, cohort, loss, arm=name) for name in arms}
