# UX and browser QA — 2026-11-14

Scope: existing main SPA retained; selected SARA-Core and final16-arm benchmark added. Scientific branch diagram replaces a generic stage-card-only presentation. Petroleum and terracotta remain primary;gold only focuses selection. Body16px,labels14px,captions13px;OS serif/sans without new font assets. Removed decorative page eyebrows,numbers,arrow glyphs and status dots from the updated surfaces;scientific directional connectors retain meaning.

## Executed journeys

Slice A: Home → final experiments;real seed selection and source disclosure. Slice B:Full2708/5278 → node2628 →45-node1-hop →122-node/189-edge2-hop;node0 global search;selected/current evidence remains separate. Slice C:workflow stage contract → explicit owner-local import → node2628 KEEP;actual B1 confidence72.5/Narrative85,unchanged Narrative class. Slice D:saved source/seed → unexecuted mask scenario →remove actual imported ID25,103→102labels →download manifest →clear private evidence →Reset. No new accuracy appears.

Final repeatable browser harness: `scripts/browser-qa.mjs`,fresh headless Microsoft Edge profile,local production preview at4175. Captures all8 routes at1440×900,390×844,768×1024;checks document overflow,rendered2708/5278,zoom/resize,keyboard zoom/Escape,1/2-hop,global-ID selection,graph download,private import/clear,scenario download,real seed change,2–4arm comparison/CSV,invalid owner fixture,reset/Back/Forward,invalid deep link,and corrupt public JSON/checksum failure. Raw execution observations and pageerror events are in ignored `.qa/v3/browser-results.json`.

## Captures

Local captures are intentionally excluded from Git/public dist. They can contain owner-local labels or mask IDs. No screenshot is a scientific source or a substitute for functional checks.

- Slice captures: `.qa/v3/A-home-desktop.png`, `A-experiments-{desktop,mobile}.png`, `B-full-desktop.png`, `B-ego-mobile.png`, `C-workflow-{desktop,mobile}.png`, `D-scenario-{desktop,mobile}.png`.
- Final captures: `.qa/v3/E-{overview,explore,workflow,agents,methods,experiments,desk,workbench}-{desktop,mobile,tablet}.png`.
- Existing historical before captures: `.qa/overview-desktop.jpg`, `.qa/full-cora-graph.jpg`, `.qa/mobile-experiments.jpg`, `.qa/redesign-agents.png`;dates30/31Oct and6Nov. These are historical comparisons,not a freshly captured748ae95 baseline. A complete controlled before/after screenshot matrix is **BLOCKED**;it was not captured before implementation.

Rendered workflow desktop and mobile explorer were visually read back. All main routes were captured and checked for page overflow at three sizes. A complete human visual readback of every disclosure/owner state,actual screen-reader speech,NVDA/VoiceOver,200% zoom and all contrast combinations is **not verified**. Native controls,skip link,focus outline,44px buttons,node-list fallback,reduced-motion CSS and accessible diagram/table alternatives are implemented;this is not a WCAG conformance claim.

## Problems found and disposition

- Original sections.tsx contained mixed encoding (invalid UTF8 dash byte):preserved source content while repairing encoding.
- Private exclusion state could outlive its owner/arm:fixed before plan construction;clear/reimport/reset tested.
- Infinite hop parameter:reject before graph traversal;negative-ID URL reports invalid state.
- Focus-selected enabled outside current graph:disabled when absent.
- Neighbor petroleum mistaken for retention:legend explicitly distinguishes focus and owner overlay;hollow nodes mean unknown evidence.
- Resize reset:resize now preserves pan/zoom;viewport cache keyed by exact ID set.
- CSV newline mismatch acrossWindows/Git:both exact byte forms explicitly pinned;LF reproduction tested.
- Browser harness initially had wrong exact-label/case/message expectations and an unavailable preview server;corrected and rerun. These failures are not reported as passing checks.

## Remaining limitations

Private current parser/sample receipts,per-node router feature terms and current checkpoint predictions are not imported. The inspector exposes unavailable states and never substitutes October samples. Current full-graph rendering is measured on available Windows/headless Edge hardware only;no controlled before/after laptop baseline or interaction latency/memory-leak stress audit is claimed. No publication,paid calls,training or new Cora science occurred.
