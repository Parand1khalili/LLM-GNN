# Exact Cora topology recovery

Date: 2026-10-30. Scope: GraphScope data/UI only. Research/SARA logic unchanged.

## Recovered source and identity

Read-only Drive traversal followed the existing frozen selection manifest's
parent chain to Prnd-project, then LLMGNN_data. General Drive search returned no
results because the archive is shared rather than present in the connected
account's root listing; direct authorized folder traversal succeeded. One initial
advanced search had invalid query syntax; it was not treated as a negative result.

- Archive: [Prnd-project/LLMGNN_data](https://drive.google.com/drive/folders/1zf2Sx1mtKYAQvHxW_dzNBUZUvyFbE6R3).
- Exact file: [cora_random_sbert.pt](https://drive.google.com/file/d/1BLOmx8MRvsWqPQLIrw78aYl5C3Uu8LyH/view).
- Original byte length: 6,898,784.
- SHA-256: `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`.
- This is the exact graph pin in the existing preparation receipt, FeatProp
  selection manifest and saved GCN protocol. It is not a downloaded replacement
  Cora variant. Other cora_openai/cora_fixed files were not substituted.

The original is `RECOVERED_EXACT` by full-byte hash. Extracted JSON and its checks
are `REPRODUCED`, not an original historical JSON file. Recovery code is
`RECONSTRUCTED`. No graph was reconstructed from sampled edges.

## Non-executing extraction boundary

The recovery script hashes the whole file before ZIP inspection. It reads
`cora_random_sbert/data.pkl` solely through the standard-library `pickletools`
opcode disassembler. It checks literal memo bindings and an exact reviewed
edge_index descriptor: LongStorage key 1, offset 0, shape (2,10858), stride
(10858,1). GLOBAL/REDUCE instructions are inspected as data, never invoked.
There is no pickle VM, `pickle.load`, `torch.load`, tensor object construction,
historical import or provider execution.

Only `cora_random_sbert/data/1` is read as tensor storage: 21,716 little-endian
signed int64 endpoint values. Label storage (`data/0`) and all other tensor
storages are never read or decoded. A test intercepts ZIP reads and verifies
that only metadata and edge storage are opened. Paper text strings already in
metadata are used for mapping checks; no new article corpus is published.

This is deliberately a fixed-source extractor, not a general .pt parser. A hash
conflict fails before opening the archive. Future variants require a separate
review, not loosening this source pin.

## Executed identity and coverage checks

| Check | Actual result |
|---|---:|
| Canonical nodes / original row indices | 2,708 / 0..2707 |
| Original directed tensor entries | 10,858 |
| Unique directed edges | 10,556 |
| Repeated directed entries | 302 |
| Unique undirected display edges | 5,278 |
| Reverse/repeated entries coalesced for display | 5,580 |
| Self-loops / isolated nodes | 0 / 0 |
| Reverse edge exists for every directed edge | PASS |
| Full target-paper text matches at the same global ID | 140/140 |
| Recorded target-degree matches | 140/140 |
| Existing research-subgraph edges present | 525/525 |
| Recorded positive and negative selected-neighbor pairs | All match |

Node indices were never reordered. Completeness follows extraction of the entire
declared edge tensor from the exact historical graph, not just subset checks.
The displayed undirected graph preserves every unique connection. The source's
302 repeated directed entries and symmetric reverse entries do not create extra
visual edges. The JSON keeps duplicate accounting and source hashes visible.

## Outputs and reproduction

- Public normalized topology: `public/data/full-topology.json`.
- Browser SHA-256 pin: `src/topology-pin.ts`.
- Versioned mapping/check receipt: `provenance/cora_topology.mapping.json`.
- Local original archive and pre-admission JSON: `.qa/` (ignored, not published).
- Pre-admission manifest SHA-256:
  `041e1d922bbfdb9f0e3565796843f1b589574b66ba2a4fe547c4c1fbd59db7d8`.
- Public topology SHA-256:
  `031bb1d3ab26ed22477cbf6ecbdbb784309850448a291e21476faaaa12339820`.

From repository root, restore the exact original bytes at the indicated local
archive path, then run:

```powershell
.\.venv\Scripts\python.exe -B web/graphscope/scripts/recover-cora-topology.py web/graphscope/.qa/cora_random_sbert.pt
cd web/graphscope
node scripts/admit-topology.mjs .qa/topology-recovery/cora_topology.manifest.json 041e1d922bbfdb9f0e3565796843f1b589574b66ba2a4fe547c4c1fbd59db7d8
node --test tests/*.test.mjs
```

The first real admission exposed an existing bug comparing sorted input keys
with an unsorted expected list; fixed before successful admission. No partial
topology was published from that failed attempt. Re-running extraction and
admission produces the same hashes.

Engineering checks: 14 JavaScript tests PASS; four Python boundary/recovery tests
PASS, including the real pinned archive read boundary; TypeScript and production
build PASS. Public bundle now has seven allowlisted files. No raw .pt, article
corpus, private manifest, GT, credentials or source maps are packaged.

Production browser QA: Full Cora displayed 2708/5278; Research Evidence returned
478/525. Node 1528 focus displayed eight nodes and ten induced edges; its complete
source degree was seven, while its selected prompt-neighbor count remained three.
Searching and selecting full-only node 0 exposed its five actual neighbors:
1184,1207,1408,1626,2414. Focus showed six nodes and seven induced edges.
The node-list renders in batches of 100 to bound DOM cost. At 390x844 the full
node-list fallback showed no document-width overflow. No application console
errors were recorded. Two browser automation input calls timed out while changing
views; subsequent state inspection confirmed the action completed. This remains
an observed interaction delay, not a claim of benchmarked frame-rate performance.
Screenshot: `.qa/full-cora-graph.jpg` (local review only). Local production preview
uses port5173; no public deployment has occurred.

The safe extractor does not recompute features or train/evaluate a model. There
is no new scientific accuracy result. Drive was read only; no upload, repository
push or deployment occurred. Local source recovery does not establish a new
independent remote backup.
