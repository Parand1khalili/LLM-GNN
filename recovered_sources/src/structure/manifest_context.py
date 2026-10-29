
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_prompt_manifest(dataset):
    """
    Resolve the frozen prompt manifest for a dataset.

    Dataset-specific naming is preferred.
    The legacy Cora filename is kept as a compatibility fallback.
    """

    dataset = str(dataset).lower()

    candidates = [
        REPO_ROOT
        / "experiments"
        / "manifests"
        / f"m1_prompt_variants_{dataset}_b256.json",
    ]

    if dataset == "cora":
        candidates.append(
            REPO_ROOT
            / "experiments"
            / "manifests"
            / "m1_prompt_variants_b256.json"
        )

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        "No frozen structural prompt manifest found.\n"
        + "\n".join(str(x) for x in candidates)
    )


def _to_int_list(ids):
    if hasattr(ids, "detach"):
        ids = ids.detach().cpu()

    if hasattr(ids, "tolist"):
        ids = ids.tolist()

    return [
        int(x)
        for x in ids
    ]


def apply_manifest_context(
    texts,
    selected_ids,
    mode,
    dataset,
):
    """
    Apply one frozen M1 structural representation.

    Supported modes:
        raw3
        rep1
        consensus

    Important:
    - retrieval is NOT recomputed here;
    - prompts are read from the frozen manifest;
    - selected target IDs must exactly match the manifest;
    - target text must exactly match the text used to build the manifest.
    """

    allowed = {
        "raw3",
        "rep1",
        "consensus",
    }

    if mode not in allowed:
        raise ValueError(
            f"Unsupported manifest structure mode: {mode}"
        )

    path = resolve_prompt_manifest(
        dataset
    )

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        manifest = json.load(f)

    manifest_dataset = str(
        manifest.get(
            "dataset",
            ""
        )
    ).lower()

    if manifest_dataset != str(dataset).lower():
        raise RuntimeError(
            f"Manifest dataset mismatch: "
            f"{manifest_dataset} != {dataset}"
        )

    selected = _to_int_list(
        selected_ids
    )

    manifest_ids = [
        int(x)
        for x in manifest[
            "target_ids"
        ]
    ]

    # --------------------------------------------------------
    # Critical experimental invariant:
    # exact same target set
    # --------------------------------------------------------

    if (
        len(selected) != len(manifest_ids)
        or
        set(selected) != set(manifest_ids)
    ):
        missing = sorted(
            set(manifest_ids)
            - set(selected)
        )

        extra = sorted(
            set(selected)
            - set(manifest_ids)
        )

        raise RuntimeError(
            "Selected targets do not match frozen M1 manifest.\n"
            f"selected={len(selected)}, "
            f"manifest={len(manifest_ids)}\n"
            f"missing={missing[:10]}\n"
            f"extra={extra[:10]}"
        )

    augmented = list(
        texts
    )

    budget = int(
        manifest[
            "structural_token_budget"
        ]
    )

    if budget != 256:
        raise RuntimeError(
            f"Unexpected structural budget: {budget}"
        )

    for node_id in selected:

        key = str(
            node_id
        )

        if key not in manifest[
            "targets"
        ]:
            raise RuntimeError(
                f"Target {node_id} missing from manifest."
            )

        record = manifest[
            "targets"
        ][key]

        # ----------------------------------------------------
        # Verify that the current dataset text is exactly the
        # text used when the frozen manifest was produced.
        # ----------------------------------------------------

        frozen_target_text = record[
            "target_text"
        ]

        current_target_text = texts[
            node_id
        ]

        if (
            frozen_target_text
            != current_target_text
        ):
            raise RuntimeError(
                f"Target text mismatch for node {node_id}."
            )

        variant = record[
            "variants"
        ][mode]

        structural_prompt = variant[
            "prompt"
        ]

        structural_tokens = int(
            variant[
                "structural_tokens"
            ]
        )

        if structural_tokens > budget:
            raise RuntimeError(
                f"Structural budget violation "
                f"for node {node_id}: "
                f"{structural_tokens} > {budget}"
            )

        # ----------------------------------------------------
        # Detect stale pre-revision manifests.
        # All final variants must share the common instruction.
        # ----------------------------------------------------

        if (
            "Usage instruction:"
            not in structural_prompt
        ):
            raise RuntimeError(
                "Prompt manifest appears stale: "
                f"common instruction missing "
                f"for node {node_id}, mode={mode}"
            )

        if (
            mode == "consensus"
            and
            "Additional semantic support:"
            not in structural_prompt
        ):
            raise RuntimeError(
                "Consensus manifest appears stale "
                f"for node {node_id}."
            )

        augmented[node_id] = (
            current_target_text.rstrip()
            + "\n\n"
            + structural_prompt
        )

    print(
        f"[STRUCTURE] mode={mode} | "
        f"targets={len(selected)} | "
        f"manifest={path.name}"
    )

    return augmented
