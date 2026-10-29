import hashlib
import random

import torch


SELECTOR_VERSION = "m4a_r1_selector_v1"


def build_undirected_adjacency(
    edge_index,
    num_nodes,
):
    adjacency = [
        set()
        for _ in range(num_nodes)
    ]

    source = edge_index[0].tolist()
    target = edge_index[1].tolist()

    for a, b in zip(source, target):
        a = int(a)
        b = int(b)

        if a == b:
            continue

        adjacency[a].add(b)
        adjacency[b].add(a)

    return [
        tuple(sorted(neighbors))
        for neighbors in adjacency
    ]


def build_true_two_hop_universe(
    target,
    adjacency,
    x_normalized,
):
    target = int(target)

    direct_neighbors = set(
        adjacency[target]
    )

    by_pair = {}

    for hop1 in adjacency[target]:
        hop1 = int(hop1)

        for hop2 in adjacency[hop1]:
            hop2 = int(hop2)

            if hop2 == target:
                continue

            if hop2 in direct_neighbors:
                continue

            pair = (
                hop1,
                hop2,
            )

            if pair in by_pair:
                continue

            target_hop1_cos = float(
                torch.dot(
                    x_normalized[target],
                    x_normalized[hop1],
                )
            )

            target_hop2_cos = float(
                torch.dot(
                    x_normalized[target],
                    x_normalized[hop2],
                )
            )

            score = (
                0.5 * target_hop1_cos
                + 0.5 * target_hop2_cos
            )

            by_pair[pair] = {
                "hop1":
                    hop1,

                "hop2":
                    hop2,

                "target_hop1_cos":
                    target_hop1_cos,

                "target_hop2_cos":
                    target_hop2_cos,

                "score":
                    score,
            }

    # Canonical universe ordering.
    return [
        by_pair[pair]
        for pair in sorted(
            by_pair.keys()
        )
    ]


def canonicalize_selected_paths(
    rows,
):
    return sorted(
        rows,
        key=lambda row: (
            int(row["hop1"]),
            int(row["hop2"]),
        ),
    )


def select_h2path3(
    target,
    adjacency,
    x_normalized,
    max_paths=3,
):
    universe = build_true_two_hop_universe(
        target=target,
        adjacency=adjacency,
        x_normalized=x_normalized,
    )

    ranked = sorted(
        universe,
        key=lambda row: (
            -float(row["score"]),
            int(row["hop1"]),
            int(row["hop2"]),
        ),
    )

    selected = ranked[
        :min(
            int(max_paths),
            len(ranked),
        )
    ]

    # Prompt presentation order is deliberately canonicalized
    # after semantic selection so ordering is not another
    # experimental variable.
    return canonicalize_selected_paths(
        selected
    )


def stable_uniform_seed(
    dataset,
    target,
):
    payload = (
        f"M4AR1|{dataset}|"
        f"{int(target)}"
    ).encode("utf-8")

    digest = hashlib.sha256(
        payload
    ).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def select_uniform2path3(
    dataset,
    target,
    adjacency,
    x_normalized,
    max_paths=3,
):
    universe = build_true_two_hop_universe(
        target=target,
        adjacency=adjacency,
        x_normalized=x_normalized,
    )

    k = min(
        int(max_paths),
        len(universe),
    )

    if k == 0:
        return []

    seed = stable_uniform_seed(
        dataset=dataset,
        target=target,
    )

    rng = random.Random(
        seed
    )

    selected_indices = rng.sample(
        range(
            len(universe)
        ),
        k=k,
    )

    selected = [
        dict(
            universe[index]
        )
        for index in selected_indices
    ]

    for row in selected:
        row["selection_seed"] = int(
            seed
        )

    # Same presentation convention as H2Path3.
    return canonicalize_selected_paths(
        selected
    )
