# Topology coverage and admission

The current 478 nodes / 525 unique undirected edges are the union of the 140
FeatProp targets, their recorded selected neighbors (at most three each), and
explicitly connected pairs among those neighbors. The exporter sorts endpoints
and deduplicates pairs, preserving their evidence-target IDs. It does not load
the original full Cora graph. Recorded degree is not displayed-subgraph degree.

The supplied earlier Explore screenshot explicitly shows **460 nodes, 467 edges,
140 targets**, partial topology and a **PageRank2** cohort. Current counts are
18 nodes and 58 edges higher. These are different selected evidence records,
not measurements of full Cora coverage. The screenshot does not support the
claim that the older full graph was larger. A different older view cannot be
audited without its source/export. Local Git history contains only the new
GraphScope implementation (introduced by 7886603), not the previous UI source.

Inspected local authentic/frozen sources and the cached recovery inventory do
not supply an admitted plain JSON full topology or prior GraphScope source.
The historical graph fingerprint is recorded, not a loaded graph. This is not
a claim that no full graph exists elsewhere in Drive. No pickle/.pt is opened.

## Missing inputs

Provide **cora_topology.json** with exactly `nodes` (sorted canonical global IDs
0..2707) and `edges` (integer endpoint pairs). Also required: mapping evidence
showing these IDs identify the same papers as the frozen project graph, and an
independently reviewed manifest. A raw Cora citation file alone is insufficient:
its paper IDs must first be mapped to this project's canonical global indices.
The expected unique edge count must come from the verified source, not a guessed
benchmark count. Directed/reversed duplicate pairs are normalized to undirected
edges; self-loops and invalid endpoints are rejected.

Manifest structure (specification, not a production fixture):

```text
source: relative filename of cora_topology.json
sha256: reviewed source-byte SHA-256
graphHash: 9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466
idSpace: canonical-zero-based-global-Cora-2708
mappingEvidence: {file: relative evidence filename, sha256: reviewed evidence hash}
rawEdgeCount: recorded count before normalization
uniqueUndirectedEdgeCount: verified unique count
```

After reviewing authenticity, full coverage and semantic ID mapping, run from
the frontend directory:

```sh
node scripts/admit-topology.mjs /path/to/reviewed-manifest.json REVIEWED_MANIFEST_SHA256
pnpm test
pnpm build
```

Admission verifies both source and mapping-evidence bytes against the reviewed
manifest, then checks all canonical IDs and that all 525 admitted research edges
are present. Hash/subset checks alone cannot prove semantic mapping or completeness;
independent manifest review is essential. The command performs no download or
research execution. It writes only sanitized topology and its browser checksum pin.
The build allowlist permits that optional public file. No GT fields are accepted.

Explore now has **Research Evidence** and **Full Cora Graph** controls. Until
admission, Full Cora explicitly says unavailable and labels the fallback partial.
When admitted it uses full adjacency, preserves research overlays and provides
full-neighbor navigation separately from the research inspector's prompt evidence.
Search/filter and selected-node focus work on the active topology. Focus is
explicitly a subset. Large graphs use deterministic display positions rather than
an expensive force layout; edges are hidden during viewport movement. Positions
have no scientific meaning. Non-research nodes have no invented article text,
annotation or verifier evidence. No full topology was admitted in this milestone.
