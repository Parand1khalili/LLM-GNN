"""Deterministic label-free post-filter for M1.

Inputs used for selection:
- node IDs
- LLM pseudo-labels
- LLM confidence scores

Ground-truth labels are not accepted by the filter.
"""

import torch

def entropy(labels):
    labels = labels.long()

    if labels.numel() == 0:
        return 0.0

    _, counts = torch.unique(
        labels,
        return_counts=True,
    )

    p = (
        counts.float()
        / counts.sum()
    )

    return float(
        -(p * torch.log(p)).sum().item()
    )


def high_good_rank(values):
    values = [
        float(x)
        for x in values
    ]

    n = len(values)

    if n <= 1:
        return torch.ones(
            n,
            dtype=torch.float64,
        )

    unique_desc = sorted(
        set(values),
        reverse=True,
    )

    position = 0
    raw_rank = {}

    for value in unique_desc:

        idxs = [
            i
            for i, x in enumerate(values)
            if x == value
        ]

        first = position
        last = (
            position
            + len(idxs)
            - 1
        )

        avg_position = (
            first + last
        ) / 2.0

        raw_rank[value] = (
            1.0
            - avg_position
            / (n - 1)
        )

        position += len(idxs)

    return torch.tensor(
        [
            raw_rank[x]
            for x in values
        ],
        dtype=torch.float64,
    )


def compute_coe(
    pseudo_labels,
):
    pseudo_labels = (
        pseudo_labels
        .clone()
        .long()
    )

    n = pseudo_labels.numel()

    current_h = entropy(
        pseudo_labels
    )

    result = torch.empty(
        n,
        dtype=torch.float64,
    )

    for i in range(n):

        keep = torch.ones(
            n,
            dtype=torch.bool,
        )

        keep[i] = False

        result[i] = (
            entropy(
                pseudo_labels[
                    keep
                ]
            )
            - current_h
        )

    return result


def label_free_ps(
    node_ids,
    pseudo_labels,
    confidences,
    remove_count,
):
    node_ids = torch.as_tensor(
        node_ids,
        dtype=torch.long,
    ).clone()

    pseudo_labels = torch.as_tensor(
        pseudo_labels,
        dtype=torch.long,
    ).clone()

    confidences = torch.as_tensor(
        confidences,
        dtype=torch.float64,
    ).clone()

    assert node_ids.ndim == 1
    assert pseudo_labels.ndim == 1
    assert confidences.ndim == 1

    n = node_ids.numel()

    assert pseudo_labels.numel() == n
    assert confidences.numel() == n

    assert (
        0
        <= remove_count
        < n
    )

    active = torch.ones(
        n,
        dtype=torch.bool,
    )

    history = []

    for step in range(
        remove_count
    ):

        active_pos = torch.where(
            active
        )[0]

        active_labels = (
            pseudo_labels[
                active_pos
            ]
        )

        active_conf = (
            confidences[
                active_pos
            ]
        )

        active_ids = (
            node_ids[
                active_pos
            ]
        )

        # Higher confidence -> stronger reason to keep.
        conf_keep = high_good_rank(
            active_conf.tolist()
        )

        # COE_i = H(Y without i) - H(Y)
        #
        # Smaller COE means removing this node damages
        # pseudo-label diversity more.
        #
        # Therefore -COE is a high-good KEEP criterion.
        coe = compute_coe(
            active_labels
        )

        diversity_keep = (
            high_good_rank(
                (-coe).tolist()
            )
        )

        # Equal weighting, matching the untuned/equal-weight
        # philosophy of the paper protocol.
        total_keep = (
            conf_keep
            + diversity_keep
        )

        min_score = float(
            total_keep.min()
        )

        candidate_local = torch.where(
            torch.isclose(
                total_keep,
                torch.tensor(
                    min_score,
                    dtype=total_keep.dtype,
                ),
                atol=1e-12,
                rtol=0.0,
            )
        )[0]

        # Deterministic, label-free implementation detail.
        # If multiple candidates tie exactly, remove
        # the one with smallest node ID.
        candidate_ids = (
            active_ids[
                candidate_local
            ]
        )

        winner = int(
            torch.argmin(
                candidate_ids
            )
        )

        remove_local = int(
            candidate_local[
                winner
            ]
        )

        remove_global = int(
            active_pos[
                remove_local
            ]
        )

        history.append(
            {
                "step":
                    step,

                "node_id":
                    int(
                        node_ids[
                            remove_global
                        ]
                    ),

                "pseudo_label":
                    int(
                        pseudo_labels[
                            remove_global
                        ]
                    ),

                "confidence":
                    float(
                        confidences[
                            remove_global
                        ]
                    ),

                "coe":
                    float(
                        coe[
                            remove_local
                        ]
                    ),

                "conf_keep":
                    float(
                        conf_keep[
                            remove_local
                        ]
                    ),

                "diversity_keep":
                    float(
                        diversity_keep[
                            remove_local
                        ]
                    ),

                "total_keep":
                    float(
                        total_keep[
                            remove_local
                        ]
                    ),
            }
        )

        active[
            remove_global
        ] = False

    return active, history
