# Versioned experiment data contracts

Existing `atlas.v2.json` and its routes are retained. The October atlas is not migrated into current final annotations. New `benchmark.v3.json` joins final aggregate CSVs independently of that historical node evidence. `benchmark.ts` rejects unknown/missing fields, incorrect identities, units, classes, cohort/loss/PS, coverage, masks, aliases, seeds or derived statistics. Bytes are SHA256-checked before schema interpretation.

| Layer | Source | Export / checks |
|---|---|---|
| Final aggregate | `reports/final_cora_gcn_results.csv` |16 ordered arms;Accuracy/SD in percent;F1/SD in0..1;coverage0..1;raw diagnostic integers;2568 test |
| Seeds | `reports/final_cora_gcn_seeds.csv` |160 rows;exact seeds0..9 per arm; independently recalculate mean/populationSD |
| Paired reference | `reports/final_cora_gcn_paired.csv` |Independent deltas/SD checked in exporter and tests;UI computes from admitted same-seed rows |
| Accounting | `reports/final_cora_gcn_provenance.json` |16arms,15specs,110new+40reused;graph/test hashes |
| Raw annotation diagnostics | `reports/six_arm_metrics.csv`, `sara_lite_metrics.csv` |Separate correct/wrong/abstained/unavailable over140;join current arms;never node GT |
| Lite actions | `reports/sara_lite_freeze.json` |22KEEP,4SWITCH,1ABSTAIN,10UNAVAILABLE |
| Historical WCE | `reports/gcn_missing_experiments_results.csv` |Only V1_r1_v1/sensitivity/wce/noPS/natural/historical_confidence.v1; separate reference74.3769,not CE pairing |
| Owner derivative | Exact pinned final manifest JSON | `.qa/owner-evidence.json` only;140sorted IDs,classorder,16labels/confidences vectors;no raw bodies,GT,features or source text |
| Graph layout | Admitted topology only | `layout.v1.json`:2708finitepositions,78components,topologySHA;deterministic bounded structural springs;no labels |

Source byte pins: `scripts/benchmark-pins.json`. Full manifest and output have separate hashes; do not update pins merely to silence a conflict. Public `ownerSHA` checks the exact allowed derivative; manual file import is explicit and never uploaded/persisted. Public per-arm source/vector/mask/fit hashes refer to different contracts; `maskSHA` is SHA256 of sorted admitted IDs serialized by exporter `encode()` (canonical JSON plus newline).

Full topology2708/5278 is complete for this admitted variant. Raw directed10858,coalesced5580; duplicate/reverse entries are not additional undirected edges. Research478/525 and text140 remain partial. Component/BFS display partitions and distances are not scientific communities or homophily results.

`graphscope.scenario.v1` contains source identities/hashes,seed,frozen GCN parameters,excluded/retained IDs and status `UNEXECUTED_WHAT_IF`; public mask IDs/count=null when unavailable. It has no accuracy/F1. Only Router-only scenarios identify R1/budget37. Plans authorize no execution. Switching arm or clearing private import discards incompatible exclusions before constructing a plan. No raw data is put in URLs; local node/arm/seed/scope navigation uses URL hash.

Build ships only four admitted JSON datasets and compiled assets; owner file,Python source,report source files,private archive,GT,checkpoints and screenshots stay outside dist. Legacy export includes previously reviewed target excerpts/parsed historical samples; this change adds no new public text or raw LLM bodies. Public publication still needs owner approval and licence/privacy review.


Cross-platform source identity: `benchmark-pins.json` records original recovered report bytes; `benchmark-repository-pins.json` records exact LF Git blob bytes. The two were checked byte-for-byte after CRLF→LF only. Each public source records both `sha256` and `repositorySHA256`; exporter accepts only these pinned identities and verifies the LF digest. This explicitly recorded newline transform is not a claim of raw byte identity. Frozen report files and their scientific pins are unchanged. Python tests reproduce the same public export from both forms and reject any extra bytes.
