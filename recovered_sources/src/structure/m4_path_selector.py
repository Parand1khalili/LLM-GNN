import hashlib
import random

import torch


SELECTOR_VERSION = "m4a_selector_v1"


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


def select_h2path3(
    target,
    adjacency,
    x_normalized,
    max_paths=3,
):
    target = int(target)

    direct_neighbors = set(
        adjacency[target]
    )

    candidates = []

    for hop1 in adjacency[target]:
        hop1 = int(hop1)

        for hop2 in adjacency[hop1]:
            hop2 = int(hop2)

            if hop2 == target:
                continue

            if hop2 in direct_neighbors:
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

            candidates.append(
                {
                    "hop1": hop1,
                    "hop2": hop2,
                    "target_hop1_cos":
                        target_hop1_cos,
                    "target_hop2_cos":
                        target_hop2_cos,
                    "score": score,
                }
            )

    # Exact path-pair deduplication.
    # Different H1 nodes leading to the same H2 node remain
    # distinct paths, as required by the frozen protocol.
    unique = {}

    for row in candidates:
        key = (
            int(row["hop1"]),
            int(row["hop2"]),
        )

        if key not in unique:
            unique[key] = row

    candidates = list(
        unique.values()
    )

    candidates.sort(
        key=lambda row: (
            -float(row["score"]),
            int(row["hop1"]),
            int(row["hop2"]),
        )
    )

    return candidates[:max_paths]


def stable_rw_seed(
    dataset,
    target,
    walk_index,
):
    payload = (
        f"M4A|{dataset}|"
        f"{int(target)}|{int(walk_index)}"
    ).encode("utf-8")

    digest = hashlib.sha256(
        payload
    ).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def single_rw2_path(
    dataset,
    target,
    walk_index,
    adjacency,
):
    target = int(target)

    seed = stable_rw_seed(
        dataset,
        target,
        walk_index,
    )

    rng = random.Random(seed)

    path = [target]

    previous = None
    current = target

    for _ in range(2):
        eligible = list(
            adjacency[current]
        )

        if previous is not None:
            eligible = [
                node
                for node in eligible
                if node != previous
            ]

        if not eligible:
            return None

        # adjacency is sorted; selection is therefore fully
        # deterministic given the frozen SHA-derived seed.
        next_node = eligible[
            rng.randrange(
                len(eligible)
            )
        ]

        path.append(
            int(next_node)
        )

        previous = current
        current = int(next_node)

    if len(path) != 3:
        return None

    return {
        "walk_index":
            int(walk_index),

        "seed":
            int(seed),

        "hop1":
            int(path[1]),

        "hop2":
            int(path[2]),
    }


def select_rw2path3(
    dataset,
    target,
    adjacency,
    walk_count=3,
):
    paths = []

    for walk_index in range(
        walk_count
    ):
        row = single_rw2_path(
            dataset=dataset,
            target=target,
            walk_index=walk_index,
            adjacency=adjacency,
        )

        if row is not None:
            paths.append(row)

    return paths
