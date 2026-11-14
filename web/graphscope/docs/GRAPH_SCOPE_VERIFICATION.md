# Verification — GraphScope SARA-Core upgrade

Date2026-11-14;baseline main748ae95. User-authorized A–E scope;no branch/PR/publication/research execution. This receipt is written before its own commit;delivery reports exact SHA,remote readback and CI result. No claim of a completed Drive backup.

## Executed checks

| Check | Actual result |
|---|---|
| `pnpm typecheck` | PASS |
| `pnpm test` |28 PASS;0fail;0skip on this owner workspace |
| `python -m unittest discover -s web/graphscope/tests -p 'test_*.py' -v` (repo root) |8 PASS,including hash rejection,LF/CRLF reproduction,and trusted topology static-ZIP boundary;no pickle VM or GT tensor read |
| `pnpm build` | PASS;9allowed public files;four exact JSON exports;no source maps/private artifacts;Vite base `/LLM-GNN/` |
| `pnpm audit --json` |0vulnerabilities across72reported dependencies |
| `node scripts/browser-qa.mjs` |37successful observations;all8routes at1440×900,390×844,768×1024;see local `.qa/v3/browser-results.json` |
| Impeccable mechanical detector on updated principal surfaces |`[]` findings;not a visual/accessibility certification |
| Independent read-only diff review |28tests,typecheck,diff check independently passed;no critical scientific/privacy defect found;focus/legend defects fixed |
| `git diff --check` | PASS;newline normalization notices only |

Local environment:Node26.13.0,pnpm11.25.0,Python3.12.14;fresh headless existing Microsoft Edge for final repeatable browser pass. CI usesNode24/Python3.12. Browser QA installs its own tooling only under ignored `.qa/browser`;no production dependency added. Private-dependent tests explicitly skip on a clean CI checkout;public build/schema/numeric tests remain required.

Data export is offline/read-only and standard-library only. Existing approved topology recovery tests statically inspect pinned ZIP members without executing a pickle;no new topology variant downloaded. Final aggregates independently joined to CSV/seed/raw reports. Eight sources have original byte hashes and explicitly verified Git LF-byte hashes;report originals remain untouched.

## Scientific readback

16arms,15specs,160arm-seed rows but150distinct fits(110new+40reused). CurrentB1=69.5288±0.3179%;currentv0=72.4377±0.5704%;Router-only=74.1005±0.2300%;Lite=72.9011±0.2592%;exact-mask=72.5078±0.4491%;historicalV1/R1CE=73.4268±0.3360%. HistoricalWCE74.3769% separated. SelectedCore has103unchanged Narrative labels/37withheld;Lite's actions are not its cause. Raw diagnostics have their own140-node denominator. SD is population SD across fixed-protocol GCN optimization seeds. No new independent-test or generalization claim.

## Public bytes

- `atlas.v2.json`: `041db9379d15d13d57f16d8f298773aad6f27ffcf0fa850332f93adeb6ab19e0`
- `full-topology.json`: `031bb1d3ab26ed22477cbf6ecbdbb784309850448a291e21476faaaa12339820`
- `benchmark.v3.json`: `747ded03ce2abe8c9f3438e4c5750bf62cc2ebb899395bb1b4b6c708ea1567e0`
- `layout.v1.json`: `8ae888f1ede0124706f1b62f39edaffd8599deac5548e68e047b59a76bb02e97`

## Browser and performance limits

Final browser checks exercise real downloads,2–4arm comparison,seed changes,2708/5278actual rendered graph counts,45-node1hop/122-node2hop at2628,global-ID0selection,keyboard zoom/Escape,resize-preserved zoom,owner import/clear,103→102scenario,invalid owner fixture,reset/history,invalid deep link and corrupted JSON rejection. No pageerror events were recorded on the successful final harness pass. Earlier failed harness attempts were corrected;their label/message/case expectations and refused preview connection were not passing tests.

A preliminary in-app run observed453.4ms graph construction. Later isolated headless passes observed roughly1.2seconds andabout86MB JS heap at a single point;different browser contexts are not a controlled performance comparison. Read exact final observation in `.qa/v3/browser-results.json`. Precomputed structural layout generation was bounded and deterministic (2708positions,78components);its test regenerates positions without labels. No claim of improved FPS or absence of memory leaks;before/after baseline,interaction latency distribution,long-task profiling and full assistive-technology review remain unverified.

## Acceptance and missing artifacts

See [every checklist item](GRAPH_SCOPE_CHECKLIST_STATUS.md),[UX/captures](GRAPH_SCOPE_UX_QA.md),[scientific contract](GRAPH_SCOPE_SARA_CORE_CONTRACT.md),and[schema](EXPERIMENT_DATA_SCHEMA.md). Current node-level sample/voting receipts,R1feature-term receipts and checkpoint prediction derivative are not admitted. Requires exact frozen GT-free source hashes/global-ID mapping and authorized sanitized adapter;October evidence cannot replace them. Complete current method recomputation is not asserted by saved-vector replay. Full screen-reader/zoom/contrast and controlled before/after baseline QA remain blocked. P1controlled execution,CiteSeer,GT overlays,andimage export are not promoted into implemented P0 claims.

## GitHub and publication boundary

Changes are scoped to GraphScope plus a nonpublishing checks workflow and this project milestone state. Unrelated `docs/NARRATIVE_SIX_ARM_PREFLIGHT_FA.md` is excluded. Account and origin independently read back as Parand1khalili/LLM-GNN;main stayed748ae95 before commit,matching remote. The requested reviewed commit/push is authorized. Check the final delivery SHA and the corresponding `GraphScope checks (no publication)` Actions run for actual readback/CI outcome;this precommit document is not itself a push receipt. Existing manual Pages publication workflow is not dispatched. Repository visibility/remotes unchanged. Pages eligibility/privacy/licensing must be checked before any separately approved publication.
