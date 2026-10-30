# Scientific protocol and method lineage

This is a reconstruction, not restored Codex-era SARA source. Offline tests do
not establish annotation accuracy, live verification success or GCN improvement.

## Primary sources personally inspected

- Chen et al., *Label-Free Node Classification on Graphs with Large Language
  Models (LLMs)*, ICLR 2024: local `llm-gnn.pdf`, Section 3 (PDF pp. 3-6),
  Appendix Table 13 (p. 23). SHA-256:
  `1e638d5ebb2bd2ad332837027457adc35c8f6853c2ba3ef74850bbdc14ac5a3b`.
- Approved thesis proposal: local `40131012_proposal.pdf`, scientific scope and
  evaluation pp. 3-9. SHA-256:
  `3a8fb9854ab5016a4f98a5ac9344158fb3b619307c7850f134517254f6025460`.
- Hash-verified recovered source snapshots and approved V2 Scientific Handoff.
  The paper/proposal were read as text; no layout/fidelity claim is made.
- The original 2026-10-20 project history, 2026-10-24 meeting report and
  2026-10-29 research-results report were not personally available in this local
  review. Their summaries in handoffs remain historical claims, not primary
  document inspection. No decision below depends on reproducing their GT data.

## Source-to-code map

| Stage | Published paper | Proposal | Historical project / reconstructed code |
|---|---|---|---|
| Selection | Section 3.2 C-Density difficulty heuristic and active-selection comparators; FeatProp is distinct | C-Density; controlled annotation budget | Frozen Cora 140 global IDs from FeatProp A²X + k-medoids. `selection/` preserves IDs; it does not silently substitute C-Density |
| Annotation | Section 3.3 confidence-aware prompting; paper selects zero-shot hybrid | Real local 1-hop/2-hop/random-walk-style context | Local B1 text-only and Narrative v0 verified 1-hop context, same underlying project LLM. `annotation/` adapters and parsed-sample replay. B1 is not the paper's B0 cache or exact original prompt/model reproduction |
| Structure context | Appendix Table 13 simple structure-aware prompts underperformed no-structure on tested Cora/CiteSeer setups | Investigate topology notation and token budgets | Narrative is the thesis extension; superiority is a research question, not inherited proof. Uniform2Path3 is not a literal random walk |
| Post-filter | Section 3.4 confidence/diversity COE, optional density | Optional confidence filtering | Frozen PS/class guard must follow recovered specific contract, not generic legacy filter; downstream initial prospective plan exposes CE/WCE **without PS** |
| Confidence loss | Section 3.5 confidence-weighted CE supported | Train lightweight GNN from pseudo-labels | `downstream/plan.py`: frozen retained-set min-max confidence, constant-confidence fallback to ones; loss `mean(CE_i*w_i)`, never division by sum of weights |
| GCN | Final classifier propagates pseudo-label information | Main scientific outcome is downstream GCN | `downstream/model.py` reuses the reviewed historical GCN class AST; no historical module import or `.pt` unpickling. Two layers, hidden 64, dropout .5 before each layer, ReLU, no batch norm, Adam .01 / weight decay .0005, exactly 30 epochs, last checkpoint, no early stopping or validation |
| Split / comparison | Framework leaves protocol choices flexible | Matched controls, calibration, budget sensitivity and ablations | Cora2708, selected140, Primary135 excluding five selected incomplete cases, Sensitivity140; common test2568 is complement of full140. Seeds0..9 paired across arms. PS removals/abstentions never enter test. `downstream/plan.py` and `evaluation/metrics.py` enforce contracts |
| SARA | Not a method from this paper | Post-paper research direction | `sara2/` and `sara3/` newly reconstructed routing/verifier/arbitration, independently labeled from published LLM-GNN |
| Evaluation | Held-out labels used only for evaluation | Raw quality/calibration, downstream accuracy, cost, scope ablations | `evaluation/` accepts explicit arrays only after decision freeze; runtime never imports it. Current tests use synthetic labels only; no real GT decoded |

## Evidence levels and current limits

- `HASH_VERIFIED`: exact bytes match a pinned original artifact. Does not imply
  runtime success or independent scientific validation.
- `OFFLINE_REPLAYED`: only the explicitly replayed stored parsed samples/votes.
  It is not full raw-body parsing or a rerun of LLM annotation.
- `TESTED`: executed synthetic contracts and observed results; any optional
  backend unavailable in the environment is `NOT_RUN`, never PASS.
- `HISTORICAL_REPORTED`: frozen M1-M4/five-prompt/GCN numbers; no training rerun.
- `LIVE_MEASURED`: requires separately authorized real execution; absent now.
- Complete raw recovery still requires all840 original response bytes, including
  726 fresh,30 supplementary,84 reused; no fabrication or parsed-label substitute.

The optional CPU backend was installed in the new local venv and a four-node
synthetic GCN forward passed. The real cached cl100k_base tokenizer also passed
historical Consensus byte-parity/budget checks on synthetic text. Installed
Python/Torch/NumPy versions differ from the successful historical environment;
see configs/offline_tested_environment.json. Optimizer/training and all140 real
target-prompt hash parity remain NOT_RUN. Primary routing excludes its five
non-Primary targets before budget allocation; both cohorts retain the same
full140-pool test complement.

The historical strongest sensitivity WCE/noPS comparison is B1 70.595794%
versus Narrative v0 73.165888%, paired +2.570093pp, as frozen historical evidence.
It is not a new reproduction, a head-to-head paper result, or a SARA-3 outcome.
Training-seed population SD is not uncertainty from independent LLM annotations.

## Prospective gates

1. Frozen-sample replay must state exact280 decision comparison and840-reference
   provenance separately from raw-byte admission. Preserve class order, prompt
   semantics, confidence arithmetic and genuine fallbacks.
2. SARA decisions use only text, allowed public class semantics and GT-free
   outputs. Never use E0/E1 correctness, wrong-node lists, final test outcomes,
   `y` or `fixed_y`. Third-class proposals require their own acceptance policy;
   they are not automatically training labels.
3. Initial proposed downstream comparisons: CE/noPS and WCE/noPS, matched
   cohort/selected pool/seeds across B1, Narrative and eligible SARA outputs.
   WCE choice follows earlier exploratory results; it is not preregistration.
4. `gcn_plan` never trains. Future `train_gcn` is default-denied, requires explicit
   separate authorization, accepts only GT-free `GraphInputs` and revalidates
   the pseudo-label plan. No evaluation, filesystem loading or saving is embedded.
5. Cora/CiteSeer were development/diagnostic datasets. Claims of generalization
   need an actually untouched cohort/dataset frozen prospectively, or must be
   labeled exploratory. Proposal 2-hop/random-walk/budget/calibration and broader
   dataset studies remain unfulfilled unless supported by specific artifacts.
6. Paid inference, actual training, GT decoding, archive writes and GitHub
   pushes remain unauthorized. Preserve negative results and mismatches.
