# LLM-GNN / SARA — Recovery and Research Handoff

**Prepared:** 2026-10-29  
**Purpose:** Transfer an evidence-grounded, actionable project state into a new ChatGPT/Codex session **before** accessing, modifying, or rebuilding a damaged repository.  
**Status of this document:** A secondary synthesis of uploaded reports, previously shared Codex results, and user-shared Google Drive listings. **It is not an independent Git, Drive, filesystem, source-code, or API audit.**

## 0. Mandatory interpretation and evidence rules

- Distinguish `DOCUMENTED_IN_UPLOADED_REPORT`, `REPORTED_BY_CODEX_IN_CHAT`, `USER_LISTED_DRIVE_ITEM`, `DIRECTLY_VERIFIED_THIS_SESSION`, `RECONSTRUCTED`, and `UNKNOWN`. Never turn a report of a successful test or upload into a new verification claim.
- The **2026-10-20** project history and **2026-10-24** meeting report / old handoff are **historical snapshots**. Their statement that G2 or SARA-3 has not begun is outdated. Later Codex reports in the conversation describe completion of SARA-2 Policy 002, E0/E1 diagnostics, offline SARA-3, P0, P1, and P2. Do not discard the earlier scientific results or stop the timeline at G1.
- Do **not** label recreated files exact recoveries unless their bytes match authoritative recorded hashes. Preserve evidence provenance and acknowledge gaps.
- The former local disk `D:` is damaged; old `D:\SARA2` and prior local Codex sessions are not assumed accessible.
- Google Drive links supplied by the user appeared in their browser, but the Google Drive connection accessible in the prior chat returned **404** when fetching at least `experiments`; account/access mismatch is plausible. Treat the user's listings as evidence that named items are present in their view, **not evidence their bytes have been read or verified**.

## 1. Scientific mission

Extend Chen et al., *Label-Free Node Classification on Graphs with Large Language Models (LLMs)* (ICLR 2024). An LLM creates pseudo-labels for selected nodes of a text-attributed graph; a GNN is trained on pseudo-labels, and ground-truth labels are reserved for independent evaluation. Compare **B1** (text-only prompt; graph still visible to downstream GCN) with **Narrative v0** (target text plus verified 1-hop neighborhood evidence) under matched conditions. SARA-2 uses confidence/agreement routing and a judge; SARA-3 investigates a blind-first-pass class-aware verifier and routing that may detect shared high-confidence mistakes.

Reference paper, approved proposal, and project history files were uploaded to the prior ChatGPT Project:
- `llm-gnn.pdf` — reference paper.
- `40131012_proposal.pdf` — approved research proposal.
- `LLMGNN_project_history_2026-10-20_FA.md` — detailed research history and FeatProp provenance.
- `LLMGNN_MEETING_REPORT_2026-10-24_FA.pdf` — meeting report through G1.
- `LLMGNN_NEW_CHAT_HANDOFF_2026-10-24_FA.md` — former handoff through G1 (stale for later SARA progress).

## 2. Historical research and strongest evidence

### Datasets / frozen FeatProp setting
- Cora 2,708 nodes, SBERT `x` shape `[2708,384]`, `edge_index` with 10,858 entries, 7 class labels.
- Selected pseudo-training nodes: FeatProp 140; Primary 135 complete-case, Sensitivity 140; shared fixed test complement 2,568 nodes. The test labels must never leak into training/prompt/router decisions.
- Canonical graph filename `cora_random_sbert.pt`, historical SHA256 `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`. Rehash any recovered candidate.
- FeatProp selection manifest historical SHA256 `dc8260974c7c0ca2e828f2d069e2896e9bcf2c363b15ca81d9f09d2803c9b12c`; find `LLMGNN_reference/experiments/matched_cora/featprop_selection_001/selection_manifest.json`.
- LLM histories: B1 and Narrative v0 were different prompting methods using the same base LLM; do not call them two independent LLMs. Historical GCN evaluations are distinct from the source paper's model/setting.

### Reported annotation accuracy after labels were frozen
- Primary B1 `92/135`, Narrative v0 `97/135`.
- Sensitivity B1 `96/140`, Narrative v0 `101/140`.

### Matched GCN experiments from historical artifacts
- 160 FeatProp GCN fits: two cohorts × four pipeline configurations × two arms × 10 seeds, followed by 20 separate agreement-only fits; 180 total in this later study (not counting older M1–M4).
- Strongest reported local result: Sensitivity, Narrative v0 + FeatProp + weighted CE **without PS** = `73.165888% ± 0.448564` across ten matched seeds. Same setup B1 = `70.595794% ± 0.344555`, paired difference `+2.570093 pp ± 0.273141`.
- Original paper's cited Cora PS-FeatProp-W benchmark `76.23% ± 0.07` is a **published comparator**, not a reproduced result from this local setup.
- Historical agreement-only Cohort Primary `71.211059% ± 0.446395` and Sensitivity `71.569315% ± 0.428862` (CE), not universally better than Narrative v0.
- Existing GCN outcomes must not be presented as improvements caused by SARA-3: **no new SARA-3 downstream GCN training was reported**.

## 3. SARA-2 status — reported in later Codex messages

- Historical frozen scientific **Policy 002** SHA256: `5a9377dd050ab243d72ddceea71725ebd70d476bae0d89254fc9e7ab4fd64c3f`.
- Receipt SHA256: `1d50eb5404acf0803241e0c33b881d5d2041195abc995a78a11eea34236a8d18`.
- Original frozen router R0 selected 37 of 140 selected nodes for judge escalation, with 0 HH nodes and 9 disagreements (as reported in subsequent SARA-3 evaluations). Preserve/reconstruct as a baseline, never silently change its behavior.
- Historical legacy G4-A/G4-B API bridge tests were **offline**, not evidence of live judge execution.

## 4. E0 / E1: critical diagnostics and their limits

E0 used node-level GT only in an explicitly isolated diagnostic of 140 FeatProp Sensitivity nodes; GT must never enter a SARA-3 runtime, prompt, selector/router, class atlas, arbitration, training or threshold selection.

Reported E0 counts:
- Both B1/v0 correct: `95`; B1 correct only: `1`; v0 correct only: `6`; both wrong: `38`.
- Of 38 both wrong, `36` agreed on the same wrong class; `2` disagreed with different wrong classes.
- At least one error on `45` nodes. Original R0 escalation missed `24` of these; `21/45` were escalated.
- Among high-high (HH) confidence agreement nodes, `21` both wrong and `72` both correct; HH therefore is not automatically reliable.
- A selection restricted to B1/v0 choices cannot correct nodes where both methods supplied the wrong class. A prospective third-class correction is a separate, higher-risk research question, not automatically approved.

E1 reported completion as `E1_COMPLETE_EXPLORATORY`. Diagnostic heuristics were exploratory and lacked evidence for an approved policy. Do not claim causality or scientifically validated router thresholds from them. Do not tune from E0/E1 GT errors and then evaluate on the same nodes as if they were independent confirmatory tests.

## 5. SARA-3: latest **reported** design and engineering checkpoints

### Offline prototype
- A GT-independent 7-class semantic **Class Atlas**, 49-pair conceptual similarity map, and content-aware risk scores.
- Routers on 140 Sensitivity nodes: R0 (SARA-2) `37` escalations, `0` HH, `9` disagreements; R1 class-aware `37`, `18` HH, `4` disagreements; R2 hybrid `37`, `7` HH, `9` disagreements.
- Blind-first-pass verifier receives target and allowed class descriptions without seeing historic votes/confidence or GT on first pass. V1 can propose a third class but **cannot accept a third-class pseudo-label into training**. A V2 that could accept a third class is experimental and **blocked for live use** until separately approved.
- Original offline prototype reported `50` passing synthetic tests. A post-seal independent review later reported passing checks on 1,394 pinned upstream phase files and the additional separately pinned G0 intake root; earlier audit FAIL was retained as history. These are **reported**, not independently re-executed here.

### P0: frozen small-scope pilot preflight
- 8 uniquely selected nodes, planned 12 verifier-pair requests, no GT used in selection.
- Group A, each Judge002 and SARA-3 V1: `[734, 2379, 2490, 682]` → 8 requests.
- Group B, SARA-3 V1 only (HH / selected by R1 but not R0): `[1031, 655, 1013, 1328]` → 4 requests.
- No independent Judge002 pairing exists for Group B; avoid claiming apples-to-apples judge vs verifier comparison there.
- Reported P0: `SARA3_PILOT_PREFLIGHT_COMPLETE`, 20 synthetic tests.

### P1: offline bridge
- Status reported `SARA3_P1_BRIDGE_OFFLINE_COMPLETE`, 32 tests + 18 independent controls passing, no live provider calls.
- 12 frozen logical wire requests, total `115,873` UTF-8 bytes, with planned exact wire hashing. Need recover bytes from actual artifacts; do not regenerate and claim historical wire hashes match without byte-for-byte comparison.
- Direct OpenAI Responses API `gpt-6-luna` was a **proposed** target under execution contracts; historical annotation used a different historical API gateway. Do not conflate endpoints, keys, model accessibility, or billing accounts.
- Conservative ledger: write an intent before dispatch; uncertain crash/timeout state means **NO AUTOMATIC RETRY**.
- Key intended parameters: `service_tier=default`, `reasoning=none`, `temperature=0`, `tools=[]`, `tool_choice=none`, `stream=false`, `store=false`, `background=false`; local input admission max 16,384 tokens; output cap 8,192; timeout 120 seconds. Verify current provider support before a live call.

### P2: offline live-readiness review
- Status reported `SARA3_P2_READINESS_REVIEW_COMPLETE`, 48 independent controls passing and 1,981 older local files reported unchanged.
- Frozen execution contract SHA256 `05e481916eeb6581a8d239347bf0514903c0dd330a87aa0071ceaa83c85a8ef1`.
- Intended endpoint for 12 *authorized* token counts: `POST /v1/responses/input_tokens`; actual provider token counts were **null / not yet authorized/executed** in the latest records available here.
- User previously indicated historical API credits and use of Luna, but current access, balance, endpoint fees, region and project-level limits were **not independently verified**.
- User discussed provisional whole-pilot local cost limit **USD 1**, including token-count requests; it is **not a provider-enforced hard billing cap**.
- A subsequent Codex Gate C prompted for non-secret account/project identification, confirmation of allowance for sending GT-free text/neighborhood/schema to the provider, and a retention policy; a response draft was supplied. **There is no confirmed receipt showing actual provider token-count calls or generation.**
- No SARA-3 live generation, no third-class acceptance, no new GCN training reported. Stop at reconstruction/inventory until new approvals.

## 6. Historical local layout (not a confirmed current filesystem inventory)

Old workspace root `D:\SARA2` with `AGENTS.md`, `sara2/` and `sara3/`.

- `sara2/`: G0–G4-related phases and E0/E1 GT-isolated diagnostics; historical subfolders were versioned/procedural.
- `sara3/`: offline prototype, post-seal review, pilot preflight, offline bridge, and live-readiness modules. Previously cited path: `sara3/pilot_live_readiness_001`.
- Old historical source Drive (Windows-mounted): `H:\My Drive\Prnd-project\LLMGNN_reference\experiments\matched_cora`.

**New architecture policy:** ONE continuously evolving codebase. Ordinary source should be modified in place, refactored, committed and pushed. No new `v001` directory for routine fixes. Immutable scientific observations, raw payloads, original datasets, frozen contracts and existing receipts are exceptional protected artifacts; keep their history and exact provenance.

## 7. User-shared Google Drive inventory: promising but not yet content-verified

Drive project root observed in user's screenshot: `Prnd-project` with `LLMGNN_reference`, `LLMGNN_data`, `env_backup`, `api_runs`, and `startup.py`.

In a subsequent user-shared list:
- Code/reference roots: `src`, `imgs`, `experiments`, `.git`, `requirements.txt`, `README.md`, `environment.yml`, `config.yaml`.
- Data roots: `partitions`, `active`, `aax`, `cora_random_sbert.pt`, `cora_openai.pt`, several versioned `cora_openai.pt.before_*` backups; also CiteSeer graph files.
- Historical per-arm directories named `b1_cora_textonly_gpt6luna_seed0`, `b1_cora_textonly_gpt6luna_alpha033_seed0`, `consensus_cora_gpt6luna_alpha033_seed0`, `raw3_cora_gpt6luna_alpha033_seed0`, `rep1_cora_gpt6luna_alpha033_seed0`.
- Historical prompt input/output/checkpoint JSON for Cora `uniform2path3`/`h2path3` and CiteSeer `uniform2path3`/`h2path3`/`textonly`/`consensus`. These are **not automatically identical to frozen FeatProp Narrative v0/B1 outputs**.

Need independently inspect Drive `experiments/matched_cora`, historical annotated votes, frozen selectors, manifests, GCN results and whether any SARA-2/3 code or source archive was separately backed up. Do not assume `.git` in Drive means any usable GitHub remote: inspect its integrity, origin and refs without mutation.

## 8. Immediate recovery plan: NO CODE CHANGES before Gate 0 decision

### Phase A — Comprehension (ChatGPT and Codex)
1. Read this handoff alongside the uploaded proposal, reference paper, detailed history, 2026-10-24 handoff and meeting report.
2. Construct a timeline distinguishing older report snapshots from newer Codex chat updates.
3. Mark unknowns and conflicts; keep observed, historical reported and inferred claims separated.
4. Explicitly identify scope and authorization: read-only repository/Drive audit; no Git writes, API, GCN, destructive actions, or updates to archival sources.

### Phase B — Discovery and recovery audit (read-only)
1. Discover *actual accessible* GitHub repositories, owners, permissions, remotes, branches, current HEAD and any tags; **do not create/push/reset/merge** during the audit.
2. Discover connected Google Drive account/context, the actual `Prnd-project`, enumerate `LLMGNN_reference/experiments/matched_cora`, `LLMGNN_data` and `api_runs`. If a supplied link produces 404, request correction of account/permissions rather than declaring files missing.
3. Record assets by path, role, size, modified date, ID, hash (when contents accessible), source, and evidence level. Search source and archives for `sara2`, `sara3`, `E0`, `E1`, `Policy 002`, P0/P1/P2, raw B1/v0 labels and 160+20 GCN outcomes.
4. Run only safe integrity checks such as hashing, parsing, imports / offline tests when local copies exist and no source mutation is required. Do not evaluate or decode test ground truth without explicit allowed scope.
5. Produce a provenance-aware `RECOVERY_INVENTORY.md`, `GAP_ANALYSIS.md`, `NEXT_SAFE_CHECKPOINT.md` and a prioritized, time/complexity-informed reconstruction plan.

### Phase C — User-approved recovery / implementation
Only after reviewing Phase B outputs and approving a specific checkpoint:
1. Restore the best existing Git repo in a **single** working tree.
2. Reconstruct missing modules in the same coherent codebase, preserving scientific frozen artifacts as evidence.
3. Write/execute targeted offline tests, then broader regressions.
4. Commit and push only to an approved **private** GitHub remote, verify remote SHA; back up non-code research artifacts in a separately verified Google Drive location.
5. Update `PROJECT_STATE.md` with evidence, exact status and remaining blockers.
6. Obtain separate explicit permission before live API requests, further GT use, new GCN trainings or expensive actions.

## 9. Expected short audit summary to the user (Persian)

- **Recovered & verified** (actual file names, path, checksum, source).
- **Available but not verified** (user-listed or metadata-only).
- **Missing / inaccessible / conflict** (not conflated).
- **Latest defensible checkpoint** (scientific vs engineering separately).
- **What must be rebuilt vs reused** (priority order).
- **GitHub status** (repo, branch, HEAD, remote, **read-only audit**, not pushed).
- **Drive status** (account, roots, files, **read-only audit**, not uploaded).
- **Safety** (GT isolation; no API/GCN run; source not modified).
- **One next user-approved action**.

## 10. User preferences and collaboration style

- Explain and report decisions in clear Persian; write technical repository instructions and code in English.
- Do not overload with repeated one-off administrative folders or giant redundant logs. Use targeted inspection, relevant skills/tools, fast tests during edits, comprehensive tests at milestones.
- Be precise about confirmed vs reported evidence; no false assurances of code accuracy or successful cloud backups.
- New meaningful development should normally be committed/pushed to private GitHub and milestone artifacts independently backed up to Drive; actual remote success needs verification.
- Never write API keys in chat, source, logs, or backups. Protect GT and original historical data.

**END HANDOFF — No live or source-modifying work is authorized by possession of this document.**
