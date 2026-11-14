# SARA-Core frozen method contract

Updated 2026-11-14. This is a UI interpretation of existing frozen research, not a new method or execution receipt.

The selected exploratory Cora method is **B1 + Narrative v0 → frozen R1-v1 risk rank → keep 103 unchanged Narrative labels / withhold 37 → 2-layer GCN, CE/noPS → separate saved evaluation**. B1 and Narrative use the same underlying LLM. Neither Agent correction nor arbitration caused the Router-only result.

| Stage | Inputs and version | Output / boundary | Implementation / artifact |
|---|---|---|---|
| Graph / targets | Original Cora-2708, FeatProp Sensitivity140 | 140 fixed global IDs; graph and prompt neighborhoods differ | `full-topology.json`, historical atlas; final manifest |
| Annotation | Current B1 text-only and Narrative local-evidence freezes | Frozen pseudo-labels and authentic confidence; old October parsed samples separate | Final manifest `arms`; annotation modules; six-arm report |
| Parser / voter | Historical three parsed samples and frozen class order | October parsed-sample re-voting only; not raw-body recovery or current-sample replay | `annotation/`, atlas source pins |
| Risk rank | `sara.router.r1_candidate.v1` | `(disagreement + candidate_mismatch + lexical_ambiguity) / 3`; exact Fraction order descending, global ID ascending ties; top37 | `src/llmgnn_sara/sara3/r1_candidate.py` |
| Admission | Frozen review pool37, Narrative140 vector | KEEP103, WITHHOLD37; retained classes unchanged. No confidence threshold or correction | Final `lite_router_only` vector and plan |
| GCN | Natural mask; CE/noPS; 2 layers, hidden64, dropout0.5, Adam LR0.01, WD0.0005,30 epochs,last checkpoint,seeds0–9,CPU1 thread | Saved fits; no browser training | `src/llmgnn_sara/downstream/`, final results/seeds |
| Evaluation | Saved predictions and fixed 2568-node complement | GT-only aggregate Accuracy/Macro-F1; withheld pool does not enter test | Separate final evaluator/provenance; no GT imported by UI |

Final manifest: `d3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e`.
Separate GT-only aggregate result: `bf2f25c1fadc231f8921bd06caf324b52aecccb424d26cb569feaab27e42ee7b`.

Router-only 74.1005 ±0.2300% vs current Narrative72.4377 ±0.5704%. Population SD over optimization seeds, not independent annotation draws. All final16 arms use CE/Natural/noPS;15 unique fit specifications,110 new+40 reused seed fits. Historical V1/R0 aliases Fusion C. Historical WCE74.3769% is a separate loss contract, not a matched CE winner.

SARA-Lite:22KEEP,4SWITCH,1ABSTAIN,10UNAVAILABLE. Lite72.9011%, exact-mask72.5078%, Router-only74.1005%. These outcomes do not establish an incremental Agent accuracy benefit; L2=NOT_ASSESSED. Rich SARA-3 roles are a separately labelled research extension.

Public access exposes aggregates/provenance. Explicit owner import adds only pinned GT-free vectors/confidences in tab memory. Missing node risk terms, current sample receipts, current checkpoint predictions and raw verifier bodies stop detailed claims; historical samples never fill those gaps. Exporter must use actual `confidence_provenance.value`, not plan sentinel weights.

Status: **LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT**. Original encoder execution receipt unavailable; test historically observed. Hashes prove identified bytes, not GT-free encoder generation. No prompt/router/budget tuning or fresh Cora experiments are authorized. What-if can only remove imported existing mask IDs and download an unexecuted plan.
