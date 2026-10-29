from pathlib import Path
import hashlib
import json

from .prompt_builder import count_tokens


REPO_ROOT = Path(__file__).resolve().parents[2]

RUNTIME_VERSION = "m4a_r1_manifest_context_v1"

EXPECTED_MANIFEST_SHA256 = {
    "cora":
        "2c09072e0471e5398b13eb1f101e4b039ae2908855026a093bac6eb77e33a167",

    "citeseer":
        "556fa571a31ae768f544a49195df8a4c0c60293902c1e90fade9056cc2b9afbf",
}

EXPECTED_COLLECTION_SHA256 = {
    "cora": {
        "H2Path3":
            "2c535e9e2558f736274891fdd4a6827cbf9d207dd3db8a06663c000f771872fe",

        "Uniform2Path3":
            "ef40eb37b4737df69ee0d691b05d9a7f11d8f3a03f5c4686382782134550303f",
    },

    "citeseer": {
        "H2Path3":
            "d8dfe383026a3cf45751ddd4af5509dc86d81264c2f3aa2c9c7851b814735626",

        "Uniform2Path3":
            "01ce0b3b8d3932aaa3049f2fb8ca93b3f39cb810d173d4059bcd1b071aa33eb9",
    },
}

MODE_TO_VARIANT = {
    "h2path3":
        "H2Path3",

    "uniform2path3":
        "Uniform2Path3",
}


def _sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def _sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def _to_int_list(ids):
    if hasattr(ids, "detach"):
        ids = ids.detach().cpu()

    if hasattr(ids, "tolist"):
        ids = ids.tolist()

    return [
        int(x)
        for x in ids
    ]


def _manifest_path(dataset):
    dataset = str(dataset).lower()

    if dataset not in EXPECTED_MANIFEST_SHA256:
        raise ValueError(
            f"M4-A-R1 unsupported dataset: {dataset}"
        )

    return (
        REPO_ROOT
        / "experiments"
        / "manifests"
        / f"m4a_r1_path_variants_{dataset}_b256.json"
    )


def _collection_sha(
    target_ids,
    targets,
    variant_name,
):
    payload = "\n".join(
        (
            f"{int(node_id)}:"
            f"{targets[str(node_id)]['variants'][variant_name]['prompt_sha256']}"
        )
        for node_id in target_ids
    )

    return _sha256_text(
        payload
    )


def load_frozen_m4_r1_manifest(
    dataset,
):
    dataset = str(dataset).lower()

    path = _manifest_path(
        dataset
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing frozen M4-A-R1 manifest: {path}"
        )

    actual_sha = _sha256_file(
        path
    )

    expected_sha = EXPECTED_MANIFEST_SHA256[
        dataset
    ]

    if actual_sha != expected_sha:
        raise RuntimeError(
            "Frozen M4-A-R1 manifest SHA mismatch. "
            f"dataset={dataset} "
            f"expected={expected_sha} "
            f"actual={actual_sha}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        manifest = json.load(f)

    if (
        manifest.get("dataset")
        != dataset
    ):
        raise RuntimeError(
            "M4-A-R1 manifest dataset mismatch."
        )

    if (
        manifest.get("status")
        != "frozen_pre_LLM_prompt_manifest"
    ):
        raise RuntimeError(
            "M4-A-R1 manifest is not frozen."
        )

    if (
        int(
            manifest[
                "matched_design"
            ][
                "structural_token_budget"
            ]
        )
        != 256
    ):
        raise RuntimeError(
            "Unexpected M4-A-R1 structural budget."
        )

    target_ids = [
        int(x)
        for x in manifest[
            "target_ids"
        ]
    ]

    targets = manifest[
        "targets"
    ]

    for variant_name in [
        "H2Path3",
        "Uniform2Path3",
    ]:
        actual_collection = _collection_sha(
            target_ids,
            targets,
            variant_name,
        )

        expected_collection = (
            EXPECTED_COLLECTION_SHA256[
                dataset
            ][
                variant_name
            ]
        )

        if (
            actual_collection
            != expected_collection
        ):
            raise RuntimeError(
                "Frozen prompt-collection SHA mismatch. "
                f"dataset={dataset} "
                f"variant={variant_name}"
            )

    return (
        path,
        manifest,
    )


def apply_m4_r1_manifest_context(
    texts,
    selected_ids,
    mode,
    dataset,
):
    dataset = str(
        dataset
    ).lower()

    mode = str(
        mode
    ).lower()

    if mode not in MODE_TO_VARIANT:
        raise ValueError(
            f"Unsupported M4-A-R1 mode: {mode}"
        )

    variant_name = MODE_TO_VARIANT[
        mode
    ]

    path, manifest = (
        load_frozen_m4_r1_manifest(
            dataset
        )
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

    if (
        len(selected)
        != len(manifest_ids)
        or
        len(set(selected))
        != len(selected)
        or
        set(selected)
        != set(manifest_ids)
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
            "Selected targets do not match "
            "frozen M4-A-R1 manifest. "
            f"selected={len(selected)} "
            f"manifest={len(manifest_ids)} "
            f"missing={missing[:10]} "
            f"extra={extra[:10]}"
        )

    augmented = list(
        texts
    )

    if len(augmented) <= max(
        manifest_ids
    ):
        raise RuntimeError(
            "Input text list is shorter than "
            "the frozen target-ID range."
        )

    zero_context = 0

    for node_id in selected:

        key = str(
            node_id
        )

        if key not in manifest[
            "targets"
        ]:
            raise RuntimeError(
                f"Target {node_id} missing "
                "from frozen M4-A-R1 manifest."
            )

        record = manifest[
            "targets"
        ][key]

        frozen_target_text = record[
            "target_text"
        ]

        current_target_text = texts[
            node_id
        ]

        if (
            current_target_text
            != frozen_target_text
        ):
            raise RuntimeError(
                f"Target text mismatch for "
                f"{dataset} node {node_id}."
            )

        if (
            _sha256_text(
                current_target_text
            )
            != record[
                "target_text_sha256"
            ]
        ):
            raise RuntimeError(
                f"Target text SHA mismatch for "
                f"{dataset} node {node_id}."
            )

        variant = record[
            "variants"
        ][
            variant_name
        ]

        structural_prompt = variant[
            "prompt"
        ]

        stored_prompt_sha = variant[
            "prompt_sha256"
        ]

        if (
            _sha256_text(
                structural_prompt
            )
            != stored_prompt_sha
        ):
            raise RuntimeError(
                f"Prompt SHA mismatch for "
                f"{dataset} node {node_id}, "
                f"variant={variant_name}."
            )

        stored_tokens = int(
            variant[
                "structural_tokens"
            ]
        )

        actual_tokens = count_tokens(
            structural_prompt
        )

        if (
            stored_tokens
            != actual_tokens
        ):
            raise RuntimeError(
                f"Structural token-count mismatch "
                f"for {dataset} node {node_id}, "
                f"variant={variant_name}: "
                f"stored={stored_tokens}, "
                f"actual={actual_tokens}"
            )

        if actual_tokens > 256:
            raise RuntimeError(
                f"Structural budget violation "
                f"for {dataset} node {node_id}."
            )

        path_count = int(
            variant[
                "path_count"
            ]
        )

        if path_count == 0:
            if structural_prompt != "":
                raise RuntimeError(
                    "Zero-path target has non-empty "
                    "structural prompt."
                )

            # Exact text-only fallback:
            # no whitespace or suffix is added.
            augmented[
                node_id
            ] = current_target_text

            zero_context += 1

        else:
            if not structural_prompt:
                raise RuntimeError(
                    "Nonzero-path target has empty "
                    "structural prompt."
                )

            if (
                "Usage instruction:"
                not in structural_prompt
            ):
                raise RuntimeError(
                    "Frozen structural prompt is "
                    "missing common instruction."
                )

            augmented[
                node_id
            ] = (
                current_target_text.rstrip()
                + "\n\n"
                + structural_prompt
            )

    print(
        f"[M4-A-R1] "
        f"mode={mode} | "
        f"variant={variant_name} | "
        f"dataset={dataset} | "
        f"targets={len(selected)} | "
        f"zero_context={zero_context} | "
        f"manifest={path.name}"
    )

    return augmented
