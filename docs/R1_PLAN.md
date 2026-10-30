# Approved offline reconstruction

The owner approved the V2 Scientific Handoff on 2026-10-30. Offline implementation
and frozen parsed-sample replay no longer require all840 raw bodies. This does
not authorize full raw-recovery claims, provider calls, GT decoding or real training.

One package: src/llmgnn_sara/{io,selection,annotation,filtering,sara2,sara3,downstream,evaluation}.
One CLI, one test suite, existing main branch. Exact source evidence remains in
recovered_sources/; only reviewed pure code is reused. Preserve unrelated user edits.

Completed engineering slices are recorded in reports/offline_implementation_verification.json.
Remaining gates: all840 raw hash admission for raw parsing/reproducibility; missing
historical Policy002 details; full real-target prompt parity; safe graph conversion
without untrusted pickle; optional numeric GCN backend validation; authorized
prospective verifier and paired training study. Synthetic success is not scientific
improvement. Private GitHub creation/push/authentication remain owner-managed;
Drive backups require an approved separate destination and verified readback.
