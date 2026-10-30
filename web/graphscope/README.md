# GraphScope v2

A static, evidence-led research atlas for LLM-GNN / SARA. React, TypeScript,
Vite and Cytoscape; system serif/sans fonts, CSS tokens and native SVG charts.
No backend, credentials, inference, training or runtime research imports.

## Local startup

Use Node.js 24 and pnpm 11.25.0. From this directory:

```sh
pnpm install --frozen-lockfile --ignore-scripts
pnpm dev
```

Open `http://127.0.0.1:5173/LLM-GNN/`. After installation, a direct startup
command works when pnpm is not on PATH:

```sh
node node_modules/vite/bin/vite.js --host 127.0.0.1
```

This Windows environment has Node on PATH but no npm/pnpm command on PATH.
Its bundled package manager can be called as:

```powershell
node C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\pnpm\bin\pnpm.cjs dev
```

The development server binds loopback. Production preview: `pnpm build`,
then `pnpm preview`; default preview URL is `http://127.0.0.1:4173/LLM-GNN/`.
Hash routes preserve section, selected global node ID and experiment condition.

## Pages and interactions

- **Overview:** research question, paper context, recorded graph, pipeline and
  Primary CE/noPS results; links into the atlas.
- **Explore:** pan/zoom/fit/reset, recorded-edge neighbor hover, node selection,
  text/ID search, target/disagreement filters and synchronized evidence inspector.
  Mobile defaults to the accessible node list. Graph keyboard: `+`, `-`, `Home`,
  left/right to a recorded adjacent node. `/` focuses search; `Escape` closes menu.
- **Workflow:** keyboard-accessible stage tabs, inputs/outputs/configuration,
  pinned sources, limitations and real-node links. SARA extensions remain separate.
- **Methods:** role, prerequisites, evidence status and expandable limitations;
  evidence-status filtering.
- **Experiments:** separate Primary/Sensitivity, CE/WCE and PS/noPS conditions;
  seed scatter, mean/population SD, paired differences, exact ten-seed table,
  retention and pseudo-label class coverage. PageRank2 has an explicit missing-source view.
- **Prediction Desk:** recorded excerpt, B1/Narrative parsed samples, confidence,
  hashes, recorded offline routing selection, safe evidence preview and saved
  GCN test-node predictions by condition/seed. Genuine verifier/arbitration outputs
  remain unavailable. Fixture judgments are excluded from production data.

## Versioned data and scientific boundaries

`public/data/atlas.v2.json` contains the research evidence. The separately pinned
`public/data/full-topology.json` now provides the exact original Cora topology:
2,708 nodes and 5,278 unique undirected edges. See [recovery evidence](TOPOLOGY_RECOVERY.md). Its reviewed digest is
in `src/data-pin.ts`. Both browser and tests verify the checksum and strict schema.
The frontend works from a checkout without the private recovery archive.

Admitted coverage:

- 478 global Cora node IDs: 140 annotation targets and 338 context nodes.
- 525 unique undirected edges, each backed by selected-neighborhood records.
- 140 target text excerpts (maximum 1,200 characters), 280 frozen annotations
  and three stored parsed samples per target/arm.
- Eight separate FeatProp conditions, ten paired seeds each: 160 historical GCN fits.
- Saved GCN predictions only for displayed context nodes, never the full test dataset.
- R0/semantic review-selection flags from a recorded offline fixture dry-run;
  six planned pilot selections. These are not model judgments or accepted labels.

Sources are SHA-256 admitted JSON, not imported historical code. Source pins
are in `scripts/source-pins.json`; original recovery metadata remains outside
the website. `RECOVERED_EXACT` denotes recovered source-byte hash matches.
`REPRODUCED` report sources denote newly executed engineering work by the other
session. Adapter/UI code is `RECONSTRUCTED`. Calculated seed means/SDs reproduce
statistics from saved values; no LLM or GCN experiment is reproduced here.

The topology is partial. Missing edges are not inferred. Source-reported degree
and displayed degree are separate. Canonical titles are unavailable; excerpts
are never split into inferred titles. The research-subgraph exporter does not open the original graph tensor;
its graph identity follows pinned source records. Full-topology recovery independently
hash-verifies the original archive and reads only its edge storage without unpickling. No untrusted pickle, GT tensor,
raw response body or historical script is loaded.

B1 is a local paper-inspired baseline, not exact paper B0. Both annotation arms
use the same underlying LLM. FeatProp is not C-Density; Uniform2Path3 is not a
literal random walk. The FeatProp corrected GCN protocol is distinct from the
older PageRank2/noPS study and its historical train/eval-mode caveat.

Historical saved outcomes do not establish SARA-3 improvement. Cora was a
development dataset. Population SD across GCN seeds is not a confidence interval
or independent annotation uncertainty. Confidence is self-reported/vote-derived,
not a calibrated probability. GCN snapshots never enter verifier preview inputs.

Missing data: PageRank2 source cohort/results; canonical titles; context-node
article text and LLM annotations; genuine verifier/arbitration/abstention outputs;
SARA GCN outcomes; checkpoint weights, probabilities and original graph tensor in the public bundle. Full sanitized topology is available separately.

The foundational paper and supplied proposal were inspected as PDF text, alongside
`docs/SCIENTIFIC_PROTOCOL.md`. Published method, proposal, historical protocol and
reconstruction choices are separate in the interface. Paper reference:
[Chen et al., ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/862819c227b16f9af64dd6ad6cfdf275-Abstract-Conference.html).

## Refresh the export

The exporter is an offline standard-library Python script isolated from the
research package. It reads only the explicitly pinned files. It checks source
hashes, global IDs, class order, prompt identities, topology evidence, shared test
IDs, paired seeds, scalar accuracy/count consistency and engineering boundaries.
New or changed sources require reviewed pin updates; conflicts fail closed.

From repository root, with the historical recovery cache available:

```powershell
.\.venv\Scripts\python.exe -B web/graphscope/scripts/export_data.py --seed-cache <historical-cache-directory>
```

Optional `--frozen` and `--authentic` override the default private local directories.
`scripts/source-pins.json` maps logical source names to expected cache filenames
and hashes. Restore those exact original JSON bytes from the owner's recovery
archive if absent. No download, model call, GT decoding or research execution
occurs during export. Do not substitute screenshot metrics or generated labels.
The checked-in sanitized export can be built without refreshing.

After a refresh, run tests/build and inspect the public diff before publication.
Do not regenerate the export concurrently with artifact-writing research work.
Recorded engineering reports are snapshots, not a live monitor of another session.

## Checks

From the frontend directory:

```sh
pnpm typecheck
pnpm test
pnpm build
pnpm audit
```

From repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s web/graphscope/tests -p test_export.py -v
```

`pnpm test` checks authentic identity joins, means, topology adjacency, search,
cohort/seed separation, missing/extra fields, leakage rejection and offline-only
routing. `pnpm build` also checks the public file allowlist, base path, size bounds,
credential patterns and exact exported bytes. These are engineering checks, not
scientific accuracy tests or a guarantee that arbitrary future content is public-safe.
See `VERIFICATION.md` for actual execution and browser QA evidence.

## Publication is pending owner approval

Vite base is `/LLM-GNN/`. The prepared workflow is
`.github/workflows/graphscope-pages.yml`. It has **manual dispatch only**, runs only
on `main`, installs/tests/builds only this frontend and uploads only its `dist/`.
It never runs Python or reads private artifacts. No push or deployment was performed.

Connected GitHub metadata verified `Parand1khalili/LLM-GNN` is private on
2026-10-30. The account plan and Pages entitlement could not be verified.
[GitHub's eligibility rules](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
require Pro, Team or Enterprise for Pages from private repositories. A private
repository does not by itself make its Pages contents private.

Publication steps, only after owner approval:

1. Verify account Pages eligibility and intended site visibility in GitHub settings.
   Review the exact sanitized JSON and any applicable excerpt/source licensing.
2. Coordinate the local commit with the other active research session. The owner
   uploads/pushes reviewed code to the verified destination; no remote is changed here.
3. In repository **Settings → Pages**, select **GitHub Actions** as the source.
4. Configure the `github-pages` environment to restrict deployment to `main` and
   require the owner as a reviewer where the account plan supports that protection.
5. Manually run **GraphScope Pages (manual publication)** on `main`, then approve
   its environment deployment if configured.
6. Verify the deployed SHA and test assets/hash routes at
   `https://parand1khalili.github.io/LLM-GNN/` before claiming a completed deployment.

Workflow structure follows [GitHub's custom-workflow guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
Do not change repository visibility to work around eligibility without separate approval.
