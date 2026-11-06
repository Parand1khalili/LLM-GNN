# Cora140 SARA-3 — Blind Review Pack V1

**Status:** owner-local, GT-free review-pack generation; **not** Human L2, label acceptance, GCN training, evaluation, model dispatch or permission to share source text.

## Source and frozen protocol

The CLI `llmgnn_sara.sara3.blind_review_pack` reads the existing **pinned GT-free** frozen/authentic inputs (not graph labels), the private, SHA-256-pinned Cora140 closeout summary, and its private terminal run. It verifies the exact 37 R0 selected Blind input payloads, bound context, gateway configuration and current seven-class atlas. The source field `target.text` may be an **excerpt**, not a complete paper.

Frozen execution context SHA-256: `c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8`

Frozen gateway contract SHA-256: `59fd3de634a4aabae97fc9df02c396c5c435819e8b7f4cdbde1fe7837a8c165f`

Immutable closeout SHA-256: `03625722e672f25acb1001b59a4f4a72dd18ab0286ddb9a58a402b73895a1abb`

## Output and safety

The owner-only directory `.local_artifacts/sara3_independent_review_v1/` contains three **content-addressed** JSON files, one each under `reviewer_a/`, `reviewer_b/` and `owner_private/`. They do **not** have fixed `blind_pack.json` names. Each reviewer pack has 37 secret-keyed case IDs, exactly the original target text, a common seven-class atlas, the same neutral rubric, and completely **blank** response fields. Reviewers see different deterministic case orderings. Neither pack includes node IDs, original predictions, routing or veto metadata, raw model responses or ground truth.

The owner-only file has the secret case-to-node mapping, private seed, and provenance/source/pack hashes. **Never distribute it to reviewers, put it in the repository, upload it to chat or public storage, or include it in diagnostic exports.** Reviewer packs also contain source text and require separate, explicit authorization before sharing outside the owner machine.

The writer reuses the repository's restrictive `PrivateAudit` ACL/permission controls. Input hashes and existing outputs are reverified. The same code and inputs replay byte-identically; an incomplete, modified, non-private or unexpected existing output **fails closed**, never overwrites or regenerates it. Recovery from incomplete outputs requires owner review, not deletion/reset.

No providers, credentials, ground-truth labels, Human Review, accepted labels, or GCN training are required or used.

## Windows PowerShell — already-created packs: verification only

Run in the existing repository root after ensuring its code matches the reviewed version:

```powershell
$env:PYTHONPATH = Join-Path $PWD "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
$py = ".\.venv\Scripts\python.exe"
$root = ".local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105"
$out = ".local_artifacts/sara3_independent_review_v1"

& $py -B -m llmgnn_sara.sara3.blind_review_pack `
  --frozen-root .local_artifacts/frozen `
  --authentic-root .local_artifacts/authentic `
  --run-root $root `
  --gateway-config configs/gapgpt_rich_v2_output4096_proposed.json `
  --output $out --verify-only
if ($LASTEXITCODE -ne 0) { throw "BLIND_PACK_FAIL_CLOSED — do not recreate or share" }
```

If the owner has **not** generated the packs, use the exact same command **without `--verify-only`**, once, after confirming the output directory does not already exist. It creates only the new private output, not the source journals.

For targeted synthetic tests (not the real Cora run):

```powershell
& $py -B -m unittest discover -s tests -p test_blind_review_pack.py -v
if ($LASTEXITCODE -ne 0) { throw "Blind review pack tests failed" }
```

The stdout JSON provides only the status (`CREATED_PRIVATE` or `VERIFIED_EXISTING`), count (37), reviewed count (0), and **relative paths plus SHA-256 digests** of the three private files. Check their disk hashes *without printing their contents*:

```powershell
# Paste ONLY the safe stdout JSON into a local variable; do not read or display the pack itself.
# When running the CLI in your own session, alternatively redirect its stdout to a private file.
# For any returned file entry (relative_path, sha256):
# (Get-FileHash (Join-Path $out $relative_path) -Algorithm SHA256).Hash.ToLowerInvariant() -eq $sha256
```

**No Human Review is started by pack generation.** Reviewer instructions and response templates remain unfilled. A separately authorized, blinded study and downstream analysis are needed before any label-correction, accuracy or GCN claim.

## Limitations

- The two reviewer packs are generated from the same frozen text. Independent **human adjudicators** and a separate disclosure/permission decision are still required.
- The frozen cohort is only 37 routed nodes out of 140; performance on the routed subset does not automatically generalize.
- These 37 case texts should not be combined with prediction/evaluation data in reviewer-facing materials. Do not use test GT to choose an Arbitration policy.
- Private local artifacts cannot be independently validated through GitHub CI, which runs only synthetic tests.
