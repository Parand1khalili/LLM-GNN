
import torch
import torch.nn.functional as F


def build_undirected_neighbors(edge_index, num_nodes):
    """
    Build deterministic undirected adjacency lists.

    Self-loops are ignored.
    Duplicate edges are removed.
    """

    neighbors = [set() for _ in range(num_nodes)]

    src = edge_index[0].detach().cpu().tolist()
    dst = edge_index[1].detach().cpu().tolist()

    for u, v in zip(src, dst):

        if u == v:
            continue

        neighbors[u].add(v)
        neighbors[v].add(u)

    return [
        sorted(list(nbrs))
        for nbrs in neighbors
    ]


def semantic_topk_1hop(
    x,
    edge_index,
    target_ids,
    k=3
):
    """
    Select the top-k semantically most similar real 1-hop neighbors.

    Parameters
    ----------
    x:
        Node feature / SBERT matrix of shape [N, D].

    edge_index:
        PyG edge_index of shape [2, E].

    target_ids:
        Iterable of target node IDs.

    k:
        Maximum number of neighbors selected per target.

    Returns
    -------
    dict:
        target_id -> {
            "degree": int,
            "neighbors": [
                {
                    "node_id": int,
                    "similarity": float
                },
                ...
            ]
        }

    Notes
    -----
    - No ground-truth labels are used.
    - Graph is treated as undirected.
    - Selection is deterministic.
    - Ties are broken by smaller node_id.
    """

    if x.ndim != 2:
        raise ValueError(
            f"x must be 2D, got shape={tuple(x.shape)}"
        )

    num_nodes = x.shape[0]

    neighbors = build_undirected_neighbors(
        edge_index=edge_index,
        num_nodes=num_nodes
    )

    # Normalize once so dot product = cosine similarity.
    x_norm = F.normalize(
        x.float(),
        p=2,
        dim=1
    )

    result = {}

    for raw_target_id in target_ids:

        target_id = int(raw_target_id)

        candidates = neighbors[target_id]

        if len(candidates) == 0:

            result[target_id] = {
                "degree": 0,
                "neighbors": []
            }

            continue

        candidate_tensor = torch.tensor(
            candidates,
            dtype=torch.long,
            device=x_norm.device
        )

        sims = torch.matmul(
            x_norm[candidate_tensor],
            x_norm[target_id]
        )

        scored = [
            (
                int(node_id),
                float(sim)
            )
            for node_id, sim in zip(
                candidates,
                sims.detach().cpu().tolist()
            )
        ]

        # Primary key: higher cosine similarity
        # Secondary key: smaller node id
        scored.sort(
            key=lambda item: (-item[1], item[0])
        )

        chosen = scored[:min(k, len(scored))]

        result[target_id] = {
            "degree": len(candidates),
            "neighbors": [
                {
                    "node_id": node_id,
                    "similarity": similarity
                }
                for node_id, similarity in chosen
            ]
        }

    return result
