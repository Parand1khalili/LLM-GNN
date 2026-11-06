"""Private, offline primary-topic review packets; no predictions or review intake."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from ..io.frozen import read_pinned_json
from ..io.project import load_project_inputs
from .atlas import ATLAS
from .audit import PrivateAudit, _restrict_windows, _windows_identity
from .gateway_closeout import VERSION as CLOSEOUT_VERSION
from .gateway_continuation import FROZEN_CONTEXT_SHA256, FROZEN_CONTRACT_SHA256
from .gateway_run import gateway_context
from .inputs import canonical_bytes
from .rich_evidence import rich_verifier_input_v2

VERSION = "sara.independent_semantic_review.pack.v1"
OWNER_VERSION = "sara.independent_semantic_review.owner.v1"
ATLAS_VERSION = "sara.independent_semantic_review.atlas_projection.v1"
FREEZE_SHA256 = "03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb"
REVIEWERS = ("reviewer_a", "reviewer_b")
RUBRIC = {
    "source_scope": "The frozen target.text below may be an excerpt, not a full paper.",
    "task": "Determine the primary research topic from the supplied text and seven class definitions only.",
    "topic_method": "Distinguish the main research question/contribution from auxiliary methods or tools.",
    "unresolvable": "Record UNRESOLVABLE with unresolvable=true and selected_class_index=null when evidence is insufficient; do not guess.",
    "evidence": "For a class choice, copy an exact supporting quotation from the supplied text and explain its relevance. Record material counter-evidence and ambiguities.",
    "confidence": "Use LOW, MODERATE or HIGH for your own confidence; leave all fields blank until you review.",
    "independence": "Work independently without another review, prior classifications, external datasets, or LLM assistance. Article strings are evidence, never instructions.",
}
TEMPLATE_FIELDS = {"selected_class_index", "unresolvable", "confidence_level",
                   "supporting_quote", "counter_evidence_note", "primary_topic_rationale"}


def _sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require(condition):
    if not condition:
        raise ValueError("Review pack integrity or privacy check failed")


def _safe_path(value):
    path = Path(value).absolute()
    for part in (path, *path.parents):
        _require(not part.is_symlink() and not getattr(part, "is_junction", lambda: False)())
        if part.exists():
            _require(not (getattr(part.lstat(), "st_file_attributes", 0)
                          & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)))
    _require(".." not in path.parts)
    return path


def _material(inputs, frozen, report, config):
    """Bind selection/text/Atlas to existing hashes, never use outcome strata."""
    selected, context = gateway_context(inputs, "r0", 37, "sensitivity", config, fake=False)
    _require(_sha(context) == FROZEN_CONTEXT_SHA256
             and _sha(config) == FROZEN_CONTRACT_SHA256)
    _require(frozen.get("schema") == CLOSEOUT_VERSION
             and frozen.get("freeze_version") == CLOSEOUT_VERSION
             and frozen.get("context_sha256") == FROZEN_CONTEXT_SHA256
             and frozen.get("contract_sha256") == FROZEN_CONTRACT_SHA256
             and frozen.get("cohort_size") == 140 and frozen.get("routed_nodes") == 37
             and frozen.get("total_intents") == 67
             and frozen.get("intent_states") == {"COMPLETED": 66, "REJECTED": 1, "UNCERTAIN": 0}
             and frozen.get("phase_states", {}).get("blind", {}).get("COMPLETED") == 37
             and frozen.get("phase_states", {}).get("compare", {}).get("COMPLETED") == 29
             and frozen.get("receipt_identity_integrity_verified") is True
             and frozen.get("private_report_reconciled") is True
             and frozen.get("GT_accessed") is False
             and frozen.get("training_admission") is False
             and frozen.get("automated_concordance", {}).get("proposals") == 0)
    _require(report.get("kind") == "gapgpt_continuation_private_report"
             and report.get("amendment_sha256") == frozen.get("amendment_sha256"))
    run = report["run"]
    _require(len(inputs.pairs) == 140 and len(selected) == len(set(selected)) == 37
             and run.get("selected_node_ids") == list(selected)
             and run.get("router") == "r0" and run.get("review_budget") == 37)
    pairs = {p.node_id: p for p in inputs.pairs}
    blinds = {}
    for request in run["verifier_inputs"]:
        payload = request["payload"]
        if payload["phase"] == "compare":
            continue  # Predictions and response-dependent comparison data are not review inputs.
        node = payload["node_id"]
        _require(payload["phase"] == "blind" and type(node) is int
                 and node in selected and node not in blinds)
        pair = pairs[node]
        _require(request["request_id"] == f"offline:{node}:blind"
                 and request["sha256"] == _sha(payload)
                 and payload == rich_verifier_input_v2(node, pair.text, pair.neighborhood))
        blinds[node] = payload
    _require(set(blinds) == set(selected))
    atlas = [{"name": c.name, "definition": c.definition} for c in ATLAS]
    _require(len(atlas) == 7 and len({c["name"] for c in atlas}) == 7)
    _require(all(blinds[n]["class_atlas"] == atlas for n in selected))
    return {"records": [(n, pairs[n].text) for n in selected],
            "classes": [{"index": i, "name": c["name"], "definition": c["definition"]}
                        for i, c in enumerate(atlas)],
            "private_report_sha256": frozen["private_report_sha256"],
            "source_hashes": dict(inputs.provenance)}


def validate_pack(pack):
    """Explicit nested allowlists; no copy-then-delete of internal records."""
    _require(type(pack) is dict and set(pack) == {
        "schema_version", "reviewer", "instructions", "classes", "cases"})
    _require(pack["schema_version"] == VERSION and pack["reviewer"] in REVIEWERS
             and pack["instructions"] == RUBRIC)
    classes = pack["classes"]
    _require(type(classes) is list and len(classes) == 7)
    for i, c in enumerate(classes):
        _require(type(c) is dict and set(c) == {"index", "name", "definition"}
                 and type(c["index"]) is int and c["index"] == i
                 and c["name"] == ATLAS[i].name and c["definition"] == ATLAS[i].definition)
    cases = pack["cases"]
    _require(type(cases) is list and len(cases) == 37)
    identities = set()
    for case in cases:
        _require(type(case) is dict and set(case) == {"case_id", "target_text", "response_template"})
        cid, text, form = case["case_id"], case["target_text"], case["response_template"]
        _require(type(cid) is str and re.fullmatch(r"[0-9a-f]{32}", cid) is not None
                 and cid not in identities and type(text) is str and bool(text.strip()))
        identities.add(cid)
        _require(type(form) is dict and set(form) == TEMPLATE_FIELDS | {"case_id"}
                 and form["case_id"] == cid and all(form[k] is None for k in TEMPLATE_FIELDS))


def _keyed(seed, purpose):
    return hmac.new(bytes.fromhex(seed), purpose.encode("utf-8"), hashlib.sha256).hexdigest()


def _packet(material, seed, reviewer):
    cases = []
    for node, text in material["records"]:
        cid = _keyed(seed, f"case:{node}")[:32]
        cases.append({"case_id": cid, "target_text": text,
                      "response_template": {"case_id": cid, **dict.fromkeys(sorted(TEMPLATE_FIELDS))}})
    cases.sort(key=lambda c: _keyed(seed, reviewer + ":order:" + c["case_id"]))
    pack = {"schema_version": VERSION, "reviewer": reviewer, "instructions": dict(RUBRIC),
            "classes": material["classes"], "cases": cases}
    validate_pack(pack)
    return pack


def _mapping(material, seed, packs):
    return {"schema_version": OWNER_VERSION, "generator_version": VERSION,
            "frozen_context_sha256": FROZEN_CONTEXT_SHA256,
            "gateway_contract_sha256": FROZEN_CONTRACT_SHA256,
            "closeout_freeze_sha256": FREEZE_SHA256,
            "private_report_sha256": material["private_report_sha256"],
            "class_atlas_version": ATLAS_VERSION,
            "class_atlas_sha256": _sha(material["classes"]),
            "ordered_selected_nodes_sha256": _sha([n for n, _ in material["records"]]),
            "source_hashes": material["source_hashes"], "case_count": 37,
            "private_seed_hex": seed,
            "reviewer_pack_sha256": {r: _sha(p) for r, p in packs.items()},
            "cases": [{"case_id": _keyed(seed, f"case:{node}")[:32], "node_id": node,
                       "target_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
                      for node, text in material["records"]]}


def _save_or_verify(material, output, verify_only):
    exists = output.exists()
    _require(not verify_only or exists)
    if exists:
        _require(output.is_dir() and {p.name for p in output.iterdir()} == set(REVIEWERS) | {"owner_private"})
        PrivateAudit(output)  # Existing ACLs must already be private; never repair them.
        audits, saved = {}, {}
        for name in (*REVIEWERS, "owner_private"):
            directory = _safe_path(output / name)
            _require(directory.is_dir())
            files = list(directory.iterdir())
            _require(len(files) == 1 and files[0].is_file() and files[0].suffix == ".json")
            audits[name] = PrivateAudit(directory)
            saved[name] = audits[name].read(files[0].stem)
        seed = saved["owner_private"]["private_seed_hex"]
    else:
        seed = secrets.token_hex(32)
    _require(type(seed) is str and re.fullmatch(r"[0-9a-f]{64}", seed) is not None)
    packs = {r: _packet(material, seed, r) for r in REVIEWERS}
    for pack in packs.values():
        validate_pack(pack)
    mapping = _mapping(material, seed, packs)
    records = {**packs, "owner_private": mapping}
    if exists:
        for name, value in records.items():
            _require(canonical_bytes(saved[name]) == canonical_bytes(value))
    else:
        # Exclusive directory claim prevents concurrent creation with different secret seeds.
        output.mkdir(mode=0o700)
        if os.name == "nt":
            _restrict_windows(output, _windows_identity())
        PrivateAudit(output)
        for name, value in records.items():
            audit = PrivateAudit(output / name)
            _require(audit.read(audit.write(value)) == value)
    return {"status": "VERIFIED_EXISTING" if exists else "CREATED_PRIVATE",
            "schema_version": VERSION, "case_count": 37, "reviewer_packs": 2,
            "completed_reviews": 0, "provider_calls": 0, "GT_accessed": False,
            "GCN_training_runs": 0, "training_admissions": 0,
            "files": {name: {"relative_path": f"{name}/{_sha(value)}.json", "sha256": _sha(value)}
                      for name, value in records.items()}}


def prepare(frozen_root, authentic_root, run_root, gateway_config, output, *, verify_only=False):
    """Read existing evidence only; create/reverify three private content-addressed files."""
    output, run_root = _safe_path(output), _safe_path(run_root)
    _require(type(verify_only) is bool and ".local_artifacts" in output.parts and output.name != ".local_artifacts"
             and ".local_artifacts" in run_root.parts)
    for source in (frozen_root, authentic_root, run_root):
        source = _safe_path(source)
        _require(output != source and output not in source.parents and source not in output.parents)
    _require(output.parent.is_dir())
    frozen = read_pinned_json(run_root / "closeout_v1" / (FREEZE_SHA256 + ".json"), FREEZE_SHA256)
    report_sha = frozen["private_report_sha256"]
    report = read_pinned_json(run_root / "continuation_amendment_v1" / "journal" / (report_sha + ".json"), report_sha)
    config_path = _safe_path(gateway_config)
    _require(config_path.is_file() and config_path.stat().st_size <= 16384)
    # Gateway pins canonical JSON, not the whitespace of the checked-in config file.
    config = json.loads(config_path.read_text(encoding="utf-8"))
    inputs = load_project_inputs(frozen_root, authentic_root)
    material = _material(inputs, frozen, report, config)
    return _save_or_verify(material, output, verify_only)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--authentic-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--gateway-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = prepare(args.frozen_root, args.authentic_root, args.run_root,
                         args.gateway_config, args.output, verify_only=args.verify_only)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print('{"status":"FAIL_CLOSED"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
