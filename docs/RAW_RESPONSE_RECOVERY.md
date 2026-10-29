# R1 raw-response recovery and input admission

## Current evidence

The initial commit `b0249a829e31e32ad6c90bc56779d6a9c1cea0ce` and clean working tree were verified before this change. Its 40 committed files had no detected high-confidence credential pattern or unwanted dataset/checkpoint/archive. This is a bounded review, not a guarantee that arbitrary future files contain no secrets.

The current Drive discovery attempt followed all 21 provider search pages (including empty pages) and separately queried the exact 48 unresolved folder names. No usable matches were returned. This is an access/discovery limitation, not evidence of deletion. The historical large-folder direct listing remains capped at 1000 items.

## One self-contained Colab script

1. Open a **new Google Colab notebook using the Google account that owns `Prnd-project`**. A CPU runtime is sufficient; no GPU, model or paid inference is needed.
2. Open `scripts/colab_recover_responses.py` locally and paste its entire contents into one code cell. Do not execute `startup.py` or any historical notebook cell.
3. Keep `RECOVERY_SCOPE = "all_selected"` to validate all 840 selected response files. This includes all 84 historical reused responses and supplies the bytes needed for full admission. Set it to `"historical_reuse"` only if you intentionally want an 84-only recovery; that cannot establish admission for the 726 fresh and 30 supplementary responses.
4. Run the cell. Its only interactive access is the official `google.colab.drive.mount` mechanism. Select the archive-owning account when prompted. It reads the existing pinned node-selection and merged-response manifests; raw filenames are never synthesized.
5. If the project is not in the ordinary mounted MyDrive location, set `SOURCE_ROOT_OVERRIDE` to the actual mounted `LLMGNN_reference` directory and rerun. The script verifies the existing manifest hashes before reading responses; it will not choose a similarly named folder silently.
6. The ZIP is saved locally at `/content/sara_recovery_exports/sara-raw-recovery-<unique>/SARA_RAW_RESPONSES.zip`, outside Drive and the historical project. Colab starts a browser download. Download before the runtime is discarded.

Only manifest-selected response JSON files and the two pinned input manifests are included, plus `RECOVERY_SHA256.json` and `RECOVERY_REPORT.json`. The report lists exact expected paths, hashes and reason codes for failures. A partial ZIP contains only validated original files; substitutes are never created. The console prints counts, the ZIP path/hash, and safe error codes, never response bodies or credentials.

No original Drive file is modified. No graph/model `.pt`, ground-truth values, historical Python code, provider or training code is loaded. No package installation is required.

## Return and verify the ZIP

Attach the downloaded ZIP to this chat and retain the displayed ZIP SHA-256. An optional local copy belongs under `.local_artifacts/recovery/` (Git-ignored), not in `recovered_sources/`.

Using the bundled Python already available on this machine, the independent admission command is:

```powershell
Set-Location 'C:\Users\Admin\Documents\ChatGPT\llm-gnn'
& 'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B scripts/verify_intake.py --bundle 'C:\Users\Admin\Downloads\SARA_RAW_RESPONSES.zip' --report reports/r1_intake_verification.json
```

Use the actual provided ZIP path. Do not run it speculatively before the ZIP exists. ZIP members are validated in place and never extracted. Duplicate names, path traversal, symlinks, unexpected members, oversize/encrypted entries, malformed checksums, CRC errors and historical hash conflicts fail closed.

For an 84-only ZIP, the tool reports the other 756 responses as unverified unless they are separately byte-verified from a local root preserving the original relative paths:

```text
python -B scripts/verify_intake.py --bundle REUSED.zip --raw-root LOCAL_RAW_ROOT --report reports/r1_intake_verification.json
```

Multiple `--bundle` arguments can be combined. Archive status claims never override independent hash checks. Exit codes: 0 = full byte admission PASS; 1 = validation FAIL; 2 = BLOCKED/incomplete. Even exit 0 ends with `STOP_FOR_USER_APPROVAL_BEFORE_REPLAY`. It does not implement or start parser/voter replay.

## Offline tests

```text
python -B -m unittest discover -s tests -v
```

These tests use synthetic byte fixtures only. They verify recovery/admission tooling, including rejection cases, no network/GT graph access, original-file immutability and the stop after admission. They are not scientific baseline replay or runtime GT-isolation validation. The actual Colab mount/download interaction must be performed by the user and is not claimed tested locally.
