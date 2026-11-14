# Capability audit and implementation plan — 2026-11-14

Baseline main 748ae95. Existing React19/TS/Vite7/Cytoscape app retained. Unrelated modified docs/NARRATIVE_SIX_ARM_PREFLIGHT_FA.md protected. Origin Parand1khalili/LLM-GNN; no branch or PR.

| Capability | Baseline evidence | Status / action |
|---|---|---|
| Historical atlas | pinned atlas.v2.json, 14 tests | Existing; revalidate |
| Full Cora | pinned topology, 2708/5278 | Existing; preset spiral and resize reset need repair |
| Node evidence | 140 targets,338 context,525 edges | Historical only; preserve |
| Final sixteen arms | reports/final_cora_gcn_* | Needs strict aggregate adapter |
| Selected SARA-Core | frozen R1-v1 and router-only arm | Needs default workflow, mask trace |
| Replay/Compare | historical paired arms | Needs multi-arm and seed replay |
| What-if | absent | Needs isolated mask inspection and stable download; no accuracy |
| Owner-local trace | private frozen GT-free manifest | Needs explicit file import; never public build |
| Real inference/training | research runners only | Intentionally outside scope |
| Public publication | manual Pages workflow | Not authorized; do not dispatch |

Slices: A versioned aggregate schema/export + refreshed home/ledger; B component-aware stable graph positions, ego and inspector; C selected method + owner-local mask trace; D saved replay/compare and unexecuted scenario manifests; E design/accessibility/QA/CI and independent diff review. Each slice runs focused tests, typecheck/build, browser flow and screenshots. Public exports allowlist only aggregates and hashes; private GT-free input stays under ignored .qa. No GT loader or research import is executed. Blocked criteria will be recorded individually rather than declared complete.


## Final disposition

Current implementation preserves the original React SPA,all historical pages/data and existing route IDs. Added aggregate benchmark/provider,full structural layout/ego explorer,current frozen mask trace,independent extensions summary,and safe replay/scenario desk. No backend,framework swap or new production dependency. No research Python modified.

Verified locally:28Node tests,8Python tests,typecheck,production/dist gate,audit0vulnerabilities;37final browser observations with three-size all-route captures. Independent read-only review found no critical scientific/privacy defect;reported viewport-scope focus and neighbor-legend issues were repaired. See GRAPH_SCOPE_VERIFICATION.md and GRAPH_SCOPE_CHECKLIST_STATUS.md for explicit limits rather than inferring completion from UI controls.

Blocked detailed evidence:current parser/sample receipts,node-level R1 terms,current checkpoint predictions. Full assistive-technology audit and controlled before/after performance/screenshot baseline are not established. These are not replaced with historical samples,fixture judgments or invented metrics. Real controlled execution and public deployment remain outside authorization.
