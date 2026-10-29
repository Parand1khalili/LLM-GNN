# LLM-GNN / SARA recovery

One continuously maintained local repository for controlled recovery of the pre-Codex research baseline.

**R1 status: BLOCKED at full raw-response replay admission.** There is no reconstructed runtime package yet. Do not run the historical source snapshots.

## Current contents

- `recovered_sources/`: 25 exact source snapshots, including all six modified and thirteen added research files (the latter count includes `Prnd-project/startup.py` outside `src`), one upstream GCN module and five frozen research scripts.
- `manifests/recovered_sources.json`: source locations, Drive IDs, original SHA-256 values and upstream relationships.
- `manifests/raw_response_requirements.json`: all 840 source responses needed for full historical replay.
- `manifests/unresolved_raw_responses.json`: 48 reused-response paths not resolved through the current Drive connector listing/search; not evidence of deletion.
- `scripts/verify_intake.py`: standard-library-only intake verification. It never imports recovered code, reads graph/model tensors, accesses providers, installs packages or trains models.
- `PROJECT_STATE.md`, `EXPERIMENT_REGISTRY.jsonl`: durable scope and status.

## Offline verification

From this directory, with an available Python 3 interpreter:

```text
python -B scripts/verify_intake.py
```

The current intake-only tool returns exit code 2 when intake hashes are intact but full raw-response admission remains blocked. An integrity or mapping error raises an error instead. Full replay admission is not implemented by this tool; even a resolved folder listing alone cannot establish it. No intake result means the parser/voter or a GCN has been reproduced.

## Recovery boundaries

The historical Drive `Prnd-project` archive stays read-only. No paid inference, provider requests, GCN training, GT decoding, unsafe `.pt` loading, `startup.py` execution or imports of unreviewed historical scripts are authorized.

Historical Codex-era SARA-2, E0/E1, SARA-3 and P0/P1/P2 source remains lost. Reports are reconstruction specifications, not executable recoveries.

To unblock replay, supply the 48 files listed in `manifests/unresolved_raw_responses.json`, retaining exact bytes and relative paths, or enable a complete readable listing. Full replay must also verify and retrieve the remaining required responses; the earlier audit byte-checked only 84/840. Never substitute frozen parsed answers or new annotations for missing raw responses.

## Git and backups

The user performs GitHub pushes manually, approximately daily. The agent prepares local commits only; it must never push, create a remote repository or change GitHub authentication. No private destination is approved or configured yet. No push command is valid until its destination is approved and verified. Never push to `CurryTang/LLMGNN`.

`manifests/drive_backup_plan.json` describes a proposed independent milestone backup. No upload or new remote backup has occurred.

Upstream reference: `CurryTang/LLMGNN`, commit `1f60eedb1452cdd997be18b5dd932a02666ee57e`. Preserve attribution and review applicable licensing before redistribution. This repository does not claim authorship of recovered sources or an independently validated executable checkpoint.
