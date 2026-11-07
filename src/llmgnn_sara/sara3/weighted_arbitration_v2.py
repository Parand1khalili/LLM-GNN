"""Fixed automatic experimental score. No GT, judge, provider or training."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile

from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs, GRAPH_SHA256
from .audit import PrivateAudit
from .correction_features import validate, ROW_FIELDS, PHASE_FIELDS, require
from .experiment import digest

VERSION = "sara.arbitration.weighted.v2"
FEATURE_SHA = "e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe"
CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs/weighted_arbitration_v2.json"
CONFIG_SHA = "42dd9643094e94eb2db14595328f8b757c31dc62b737bede77ce69f53df48863"
WEIGHTS = {"P": 2, "N": 1, "Q": 1, "T": 1, "A": -1, "C": -2, "U": -1}


def load_graph(path):
    """Fixed hash-admitted storage extraction: never invoke pickle or read y storage.

    The reviewed source descriptor for x is FloatStorage32, shape2708x384,
    offset0/stride384,1. edge_index is LongStorage1, shape2x10858. The full
    historical SHA fixes these descriptors; no arbitrary torch archive supported.
    """
    import numpy as np
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)))
    require(path.stat().st_size <= 32 * 1024 * 1024)
    blob = path.read_bytes()
    require(hashlib.sha256(blob).hexdigest() == GRAPH_SHA256)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())))
        xbytes = archive.read("cora_random_sbert/data/32")
        ebytes = archive.read("cora_random_sbert/data/1")
    require(len(xbytes) == 2708 * 384 * 4 and len(ebytes) == 21716 * 8)
    x = np.frombuffer(xbytes, dtype="<f4").reshape(2708, 384).astype("float64")
    require(bool(np.isfinite(x).all()))
    values = struct.unpack("<21716q", ebytes)
    adjacent = [set() for _ in range(2708)]
    for a, b in zip(values[:10858], values[10858:]):
        require(0 <= a < 2708 and 0 <= b < 2708 and a != b)
        adjacent[a].add(b)
    require(all(a in adjacent[b] for a, ns in enumerate(adjacent) for b in ns))
    return x, adjacent, {"graph_sha256": GRAPH_SHA256,
                         "embedding_storage_sha256": hashlib.sha256(xbytes).hexdigest(),
                         "edge_storage_sha256": hashlib.sha256(ebytes).hexdigest(),
                         "tensor_storages_read": ["32", "1"], "label_storage_read": False}


def support(node, agent, narrative, x, adjacency, seeds, cfg):
    """Only GT-free baseline seed labels; target excluded from its own support."""
    import numpy as np
    require(x.ndim == 2 and len(adjacency) == len(x) and bool(np.isfinite(x).all()))
    require(type(node) is int and 0 <= node < len(x))
    require(all(type(i) is int and 0 <= i < len(x) and type(k) is int and 0 <= k < 7 for i, k in seeds.items()))
    require(all(type(n) is int and 0 <= n < len(x) and n != i
                for i, ns in enumerate(adjacency) for n in ns))
    require(all(i in adjacency[n] for i, ns in enumerate(adjacency) for n in ns))
    p, n = None, None
    counts, cosine = {}, {}
    norm = np.linalg.norm(x, axis=1)
    for label in sorted({agent, narrative}):
        ids = sorted(i for i, k in seeds.items() if k == label and i != node and norm[i] > 0)
        counts[str(label)] = len(ids)
        cosine[str(label)] = None
        if len(ids) >= cfg["prototype_min_samples"] and norm[node] > 0:
            prototype = np.mean(x[ids] / norm[ids, None], axis=0)
            pn = float(np.linalg.norm(prototype))
            if pn > 0:
                cosine[str(label)] = float(np.dot(x[node] / norm[node], prototype / pn))
    a, b = cosine[str(agent)], cosine[str(narrative)]
    if a is not None and b is not None:
        p = int(a >= cfg["prototype_cosine_min"] and a - b >= cfg["prototype_cosine_margin"])
    neighbors = sorted(adjacency[node])
    reliable = [i for i in neighbors if i in seeds and i != node]
    density = (sum(j in adjacency[i] for ix, i in enumerate(neighbors) for j in neighbors[ix+1:])
               / (len(neighbors) * (len(neighbors)-1) / 2)) if len(neighbors) >= 2 else None
    if len(reliable) >= cfg["neighbor_min_samples"] and density is not None and density >= cfg["neighbor_density_min"]:
        ac, bc = sum(seeds[i] == agent for i in reliable), sum(seeds[i] == narrative for i in reliable)
        n = int(ac / len(reliable) >= cfg["neighbor_support_fraction"] and ac > bc)
    return {"P": p, "N": n, "prototype_counts": counts, "cosines": cosine,
            "reliable_neighbor_count": len(reliable), "neighborhood_density": density}


def decide(row, components, cfg):
    """Pure rule. A direct caller must supply authenticated frozen phase features."""
    require(digest(cfg) == CONFIG_SHA and set(row) == ROW_FIELDS and set(components) == {"P", "N"})
    require(all(v is None or type(v) is int and v in (0, 1) for v in components.values()))
    baseline = row["narrative_class"]
    require(type(baseline) is int and 0 <= baseline < 7)
    result = {"policy_version": VERSION, "decision": "KEEP_NARRATIVE", "label": baseline,
              "agent_class": None, "score": None, "components": None,
              "third_class": None, "reason": "UNCHANGED", "training_eligible": False,
              "l2_status": "NOT_ASSESSED"}
    phases = row["blind"], row["compare"]
    require(all(type(p) is dict and set(p) == PHASE_FIELDS for p in phases))
    require(row["shared_support"] is None or type(row["shared_support"]) is int and row["shared_support"] >= 0)
    require(row["topic_consistent"] is None or type(row["topic_consistent"]) is bool)
    for phase in phases:
        require(all(phase[k] is None or type(phase[k]) is bool for k in ("auxiliary_warning", "uncertainty")))
        require(phase["counter_count"] is None or type(phase["counter_count"]) is int and phase["counter_count"] >= 0)
    if any(p["state"] != "COMPLETED" or p["l1"] != "PASS" or p["abstain"] is not False
           or type(p["class_index"]) is not int or not 0 <= p["class_index"] < 7 for p in phases):
        return {**result, "decision": "NO_VALID_AGENT_RESPONSE", "reason": "L1_ABSTENTION_OR_MISSING_PHASE"}
    a, b = phases
    if a["class_index"] != b["class_index"]:
        return {**result, "reason": "PHASE_CLASS_DISAGREEMENT"}
    label = a["class_index"]
    third = label not in (row["b1_class"], baseline)
    def present(key, numeric=False):
        values = [p[key] for p in phases]
        if any(v is not None and (v > 0 if numeric else v is True) for v in values): return 1
        return None if any(v is None for v in values) else 0
    terms = {**components, "Q": None if row["shared_support"] is None else int(row["shared_support"] > 0),
             "T": None if row["topic_consistent"] is None else int(row["topic_consistent"]),
             "A": present("auxiliary_warning"), "C": present("counter_count", True), "U": present("uncertainty")}
    score = sum(WEIGHTS[k] * (v if v is not None else 0) for k, v in terms.items())
    result.update(agent_class=label, third_class=third, components=terms, score=score)
    if label == baseline: return result
    if terms["P"] != 1 and terms["N"] != 1:
        return {**result, "reason": "NO_POSITIVE_PROTOTYPE_OR_NEIGHBOR_SUPPORT"}
    threshold = cfg["third_class_threshold"] if third else cfg["candidate_threshold"]
    if score < threshold: return {**result, "reason": "BELOW_THRESHOLD"}
    return {**result, "decision": "SWITCH_TO_AGENT", "label": label, "reason": "EXPERIMENTAL_SCORE_PASS"}


def run(table, inputs, x, adjacency, cfg):
    validate(table)
    require(digest(cfg) == CONFIG_SHA and cfg["version"] == VERSION and cfg["weights"] == WEIGHTS)
    pairs = {p.node_id: p for p in inputs.pairs}
    require(all(r["b1_class"] == pairs[r["node_id"]].b1.class_index and
                r["narrative_class"] == pairs[r["node_id"]].narrative_v0.class_index for r in table["rows"]))
    result = []
    for router in ("r0", "r1_v1"):
        rows = [r for r in table["rows"] if r["router"] == router]
        selected = {r["node_id"] for r in rows}
        seeds = {p.node_id: p.narrative_v0.class_index for p in inputs.pairs if p.node_id not in selected
                 and p.agrees and min(p.b1.confidence, p.narrative_v0.confidence) >= cfg["seed_min_confidence"]}
        for row in rows:
            agent = row["blind"]["class_index"]
            evidence = {"P": None, "N": None}
            if type(agent) is int:
                evidence = support(row["node_id"], agent, row["narrative_class"], x, adjacency, seeds, cfg)
            decision = decide(row, {k: evidence[k] for k in ("P", "N")}, cfg)
            result.append({"router": router, "node_id": row["node_id"], "narrative_class": row["narrative_class"],
                           "support": evidence, **decision})
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("features", "graph", "frozen-root", "authentic-root", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args(argv)
    try:
        table = read_pinned_json(args.features, FEATURE_SHA)
        inputs = load_project_inputs(args.frozen_root, args.authentic_root)
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        require(".local_artifacts" in args.output.absolute().parts)
        audit = PrivateAudit(args.output)
        # Freeze the prospective rule BEFORE scoring graph evidence or opening GT.
        rule_sha = audit.write({"version": VERSION, "config": cfg})
        x, adjacent, provenance = load_graph(args.graph)
        rows = run(table, inputs, x, adjacent, cfg)
        report = {"schema": VERSION, "rule_sha256": rule_sha, "source_feature_sha256": FEATURE_SHA,
                  "graph_provenance": provenance, "config": cfg, "rows": rows, "training_admissions": 0}
        sha = audit.write(report); require(audit.read(sha) == report)
        print(json.dumps({"status": "WEIGHTED_V2_FROZEN_NO_GT", "rule_sha256": rule_sha,
                          "artifact_sha256": sha, "routers": {r: dict(Counter(d["decision"] for d in rows if d["router"] == r))
                                                                  for r in ("r0", "r1_v1")}}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile):
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
