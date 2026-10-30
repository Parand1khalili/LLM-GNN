# GraphScope v2 verification

Subsequent topology milestone: see [TOPOLOGY_RECOVERY.md](TOPOLOGY_RECOVERY.md).
The original graph is now hash-admitted through non-executing static ZIP extraction:
2,708 nodes and 5,278 unique undirected edges. Updated checks: 14 JavaScript and
four Python tests PASS, TypeScript/build PASS; seven public files. Earlier numbers
below describe the initial research-subgraph UI milestone.

Date: 2026-10-30, America/Los_Angeles. Engineering milestone, not a scientific run.
Research base: `3e56105d51017bcd19729b417bf3eea3987c0c11` on existing `main`.

## Executed checks

- Node 24.22.1; pnpm 11.25.0; React 19.2.0; Vite 7.3.7; TypeScript 5.9.3;
  Cytoscape 3.33.1. Exact dependency lockfile included.
- `pnpm test`: **10/10 PASS**. Includes authentic ID/annotation/topology joins,
  all-node Cytoscape adjacency, actual historical means, search/filter behavior,
  leakage/mapping/edge rejection, paired seed provenance and offline routing bounds.
- Python exporter boundary tests: **2/2 PASS** (hash conflict, invalid confidence).
- `pnpm build`: TypeScript and production Vite build **PASS**. Six allowed public
  files; source maps disabled; public file/credential-pattern/size checks **PASS**.
- `pnpm audit`: **0 known advisories** across 72 dependency entries, including
  build dependencies. This is an advisory-database result, not proof of zero risk.
- Export rerun produced exactly the same 648,122 bytes and SHA-256:
  `041db9379d15d13d57f16d8f298773aad6f27ffcf0fa850332f93adeb6ab19e0`.
- Production `/LLM-GNN/` page and sanitized export loaded in the in-app browser,
  passing browser SHA-256 and runtime schema checks.

## Browser QA

Executed against local development and production-preview servers:

- Desktop: all six sections opened; node-ID search and node-list selection changed
  inspector and URL to node 1013 with authentic text and predictions.
- Direct canvas click after zoom selected real node 2628 and synchronized its
  recorded excerpt/metadata. Zoom controls, keyboard fit, graph pan and reset
  were exercised. Hover on the selected node visibly highlighted its recorded
  adjacent nodes and incident edges; selection preserves that highlight.
- Workflow stage selection exposed annotation inputs/outputs/configuration;
  keyboard ArrowRight changed the selected stage.
- Methods evidence filter displayed only the planned downstream/verifier method.
- Experiments switched to Sensitivity/WCE/noPS and displayed source-derived
  `70.60%` versus `73.17%`; PageRank2 displayed its explicit unavailable state.
- Prediction Desk displayed parsed sample hashes, unavailable genuine verifier
  results and offline routing flags. Context node 1014 showed both saved GCN
  class predictions for seed 0; target 1013 showed no held-out GCN snapshot.
- Mobile 390×844: menu, default node-list alternative, search/selection, Workflow
  keyboard tabs and experiment PS control worked. No document-width overflow.
- Tablet 768×1024: Prediction Desk rendered without document-width overflow.
- Production desktop checked at 1280×900. Temporary viewport override reset
  after QA. No application console errors observed during the inspected flows.

Local screenshots are ignored under `.qa/` and are not published. Images include
desktop Overview, mobile Experiments and tablet Prediction Desk. They are review
evidence, not original historical artifacts.

## Resolved issues and verification limits

Initial sandboxed Vite configuration resolution failed when esbuild could not
read a parent directory. Authorized local build outside that restriction passed;
TLS verification was not disabled. Browser review found Cytoscape's injected
unlayered positioning overriding layered CSS; an explicit scoped rule fixed the
zero-height canvas. A dependency audit identified advisories in initial Vite
7.2.2; upgrading to 7.3.7 yielded zero reported advisories. A deprecated redundant
types stub was removed. Production chunks were separated to stay under Vite's
default chunk warning threshold.

Data tests exercise recorded-edge adjacency; they do not independently recover
the original graph tensor. Hover behavior uses Cytoscape's admitted adjacency;
all possible pointer/device combinations and full screen-reader audits were
not exhaustively tested. Network/checksum failure UI is implemented; malformed
exports are covered by automated boundary tests. No claim of exhaustive browser
fault injection or WCAG certification is made.

The Python research package was not edited or imported by this UI work. Its full
suite was not rerun here; the concurrent research session owns that verification.
Source artifacts were read-only. No API generation, GT decoding, training,
historical Drive write, remote change, GitHub push or deployment occurred.

## Scientific scope and provenance

The export includes 478 nodes, 525 recorded edges, 140 truncated target excerpts,
280 annotations, eight matched FeatProp conditions and 160 saved GCN fits. Means,
population SD and paired deltas are recomputed from historical scalar accuracies.
Primary135 and Sensitivity140, PS/noPS and CE/WCE remain separate. GCN class
snapshots are exported only for 338 displayed context nodes, not the full dataset.

Pinned engineering reports provide offline review-selection flags only. Fixture
model outputs, accepted labels and final arbitrations are excluded. No new SARA
annotation quality, verifier accuracy or downstream benefit is established.
Original response hashes are references, not proof that response bodies were read.

Source hashes/logical identities are recorded in `scripts/source-pins.json` and
the public allowlisted provenance records. The recoverable original cache and
private manifests remain separate from public assets. No Drive upload or readback
was performed. Local export reproducibility is not a verified remote backup.

GitHub metadata verified the requested repository is private. Pages entitlement
and account plan remain unverified. Publication needs owner approval and manual
steps in README; the prepared workflow has manual dispatch only.

## Git coordination

The other research session was inspected before implementation. Its active work
was preserved. It completed research commit `3e56105` and was independently
observed idle before preparing this UI commit. Only this frontend, its requested
Pages workflow and the concise root state pointer are staged by this session.
Resolve the UI commit with `git log -1 -- web/graphscope`; this document does not
claim to contain its own commit SHA. GitHub status remains `PUSH_PENDING` until
the expected commit is independently verified at the remote.
