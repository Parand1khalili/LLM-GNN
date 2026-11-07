# Executed fusion quality and planned GCN matrix

2026-11-07. EXPLORATORY_NOT_INDEPENDENT. No GCN training or real experimental admission.

These tables are deterministic aggregate projections of the private outcome and grid hashes below.

## primary label quality

|Arm|Accepted|Abstained|Correct accepted|Coverage %|Selective accuracy %|Macro-F1 accepted only|
|---|---:|---:|---:|---:|---:|---:|
|A_B1|135|0|92|100.0000|68.1481|0.666327|
|B_NARRATIVE|135|0|97|100.0000|71.8519|0.697913|
|C_BASELINE_FUSION|89|46|69|65.9259|77.5281|0.768899|
|D_P1_r0|114|21|85|84.4444|74.5614|0.717855|
|D_P1_r1_v1|103|32|78|76.2963|75.7282|0.756410|
|E_P2_r0|116|19|86|85.9259|74.1379|0.714868|
|E_P2_r1_v1|103|32|78|76.2963|75.7282|0.756410|

|Arm|Class0|Class1|Class2|Class3|Class4|Class5|Class6|
|---|---:|---:|---:|---:|---:|---:|---:|
|A_B1|9|31|15|12|33|5|30|
|B_NARRATIVE|9|34|14|12|33|4|29|
|C_BASELINE_FUSION|7|23|12|8|15|3|21|
|D_P1_r0|11|29|14|11|19|5|25|
|D_P1_r1_v1|11|27|13|8|18|3|23|
|E_P2_r0|11|30|14|11|20|5|25|
|E_P2_r1_v1|11|27|13|8|18|3|23|

|Fusion arm|Agent-selected|Third class|Kept C|Revised C|Added C|Dropped C|Disagreement ->B1 /Narrative /Third /Abstain|
|---|---:|---:|---:|---:|---:|---:|---|
|D_P1_r0|25|7|89|0|25|0|3/3/0/3|
|D_P1_r1_v1|22|4|87|2|14|0|2/3/0/4|
|E_P2_r0|27|7|89|0|27|0|3/3/0/3|
|E_P2_r1_v1|22|4|87|2|14|0|2/3/0/4|

|Fusion arm|Reference|Agent-selected n|Changed class|Fix|Harm|Both wrong|Net|
|---|---|---:|---:|---:|---:|---:|---:|
|D_P1_r0|b1_class|25|10|5|2|7|3|
|D_P1_r0|narrative_class|25|10|4|4|5|0|
|D_P1_r1_v1|b1_class|22|7|3|1|7|2|
|D_P1_r1_v1|narrative_class|22|6|2|2|6|0|
|E_P2_r0|b1_class|27|10|5|2|8|3|
|E_P2_r0|narrative_class|27|10|4|4|6|0|
|E_P2_r1_v1|b1_class|22|7|3|1|7|2|
|E_P2_r1_v1|narrative_class|22|6|2|2|6|0|


|Fusion arm|Third class reference|n|Fix|Harm|Both wrong|Net|
|---|---|---:|---:|---:|---:|---:|
|D_P1_r0|b1_class|7|3|2|2|1|
|D_P1_r0|narrative_class|7|3|2|2|1|
|D_P1_r1_v1|b1_class|4|1|1|2|0|
|D_P1_r1_v1|narrative_class|4|1|1|2|0|
|E_P2_r0|b1_class|7|3|2|2|1|
|E_P2_r0|narrative_class|7|3|2|2|1|
|E_P2_r1_v1|b1_class|4|1|1|2|0|
|E_P2_r1_v1|narrative_class|4|1|1|2|0|

## sensitivity label quality

|Arm|Accepted|Abstained|Correct accepted|Coverage %|Selective accuracy %|Macro-F1 accepted only|
|---|---:|---:|---:|---:|---:|---:|
|A_B1|140|0|96|100.0000|68.5714|0.676544|
|B_NARRATIVE|140|0|101|100.0000|72.1429|0.707280|
|C_BASELINE_FUSION|93|47|72|66.4286|77.4194|0.770751|
|D_P1_r0|118|22|88|84.2857|74.5763|0.721671|
|D_P1_r1_v1|108|32|82|77.1429|75.9259|0.759403|
|E_P2_r0|120|20|89|85.7143|74.1667|0.718822|
|E_P2_r1_v1|108|32|82|77.1429|75.9259|0.759403|

|Arm|Class0|Class1|Class2|Class3|Class4|Class5|Class6|
|---|---:|---:|---:|---:|---:|---:|---:|
|A_B1|9|32|15|12|33|6|33|
|B_NARRATIVE|9|35|14|12|33|5|32|
|C_BASELINE_FUSION|7|24|12|8|15|4|23|
|D_P1_r0|11|30|14|11|19|6|27|
|D_P1_r1_v1|11|28|13|8|18|4|26|
|E_P2_r0|11|31|14|11|20|6|27|
|E_P2_r1_v1|11|28|13|8|18|4|26|

|Fusion arm|Agent-selected|Third class|Kept C|Revised C|Added C|Dropped C|Disagreement ->B1 /Narrative /Third /Abstain|
|---|---:|---:|---:|---:|---:|---:|---|
|D_P1_r0|25|7|93|0|25|0|3/3/0/3|
|D_P1_r1_v1|23|4|91|2|15|0|2/3/0/4|
|E_P2_r0|27|7|93|0|27|0|3/3/0/3|
|E_P2_r1_v1|23|4|91|2|15|0|2/3/0/4|

|Fusion arm|Reference|Agent-selected n|Changed class|Fix|Harm|Both wrong|Net|
|---|---|---:|---:|---:|---:|---:|---:|
|D_P1_r0|b1_class|25|10|5|2|7|3|
|D_P1_r0|narrative_class|25|10|4|4|5|0|
|D_P1_r1_v1|b1_class|23|7|3|1|7|2|
|D_P1_r1_v1|narrative_class|23|6|2|2|6|0|
|E_P2_r0|b1_class|27|10|5|2|8|3|
|E_P2_r0|narrative_class|27|10|4|4|6|0|
|E_P2_r1_v1|b1_class|23|7|3|1|7|2|
|E_P2_r1_v1|narrative_class|23|6|2|2|6|0|


|Fusion arm|Third class reference|n|Fix|Harm|Both wrong|Net|
|---|---|---:|---:|---:|---:|---:|
|D_P1_r0|b1_class|7|3|2|2|1|
|D_P1_r0|narrative_class|7|3|2|2|1|
|D_P1_r1_v1|b1_class|4|1|1|2|0|
|D_P1_r1_v1|narrative_class|4|1|1|2|0|
|E_P2_r0|b1_class|7|3|2|2|1|
|E_P2_r0|narrative_class|7|3|2|2|1|
|E_P2_r1_v1|b1_class|4|1|1|2|0|
|E_P2_r1_v1|narrative_class|4|1|1|2|0|

## GCN draft masks: sensitivity / natural

|Arm|CE/noPS|WCE/noPS|CE/PS|WCE/PS|
|---|---|---|---|---|
|A_B1|140 draft|140 draft|98 draft|98 draft|
|B_NARRATIVE|140 draft|140 draft|98 draft|98 draft|
|C_BASELINE_FUSION|93 draft|93 draft|66 draft|66 draft|
|D_P1_r0|118 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|
|E_P2_r0|120 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|
|D_P1_r1_v1|108 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|
|E_P2_r1_v1|108 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|

## GCN draft masks: sensitivity / matched_all_arms

|Arm|CE/noPS|WCE/noPS|CE/PS|WCE/PS|
|---|---|---|---|---|
|A_B1|93 draft|93 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|B_NARRATIVE|93 draft|93 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|C_BASELINE_FUSION|93 draft|93 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|D_P1_r0|93 draft|93 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|E_P2_r0|93 draft|93 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|D_P1_r1_v1|93 draft|BLOCKED confidence|BLOCKED common PS mask|BLOCKED common PS mask|
|E_P2_r1_v1|93 draft|BLOCKED confidence|BLOCKED common PS mask|BLOCKED common PS mask|

## GCN draft masks: primary / natural

|Arm|CE/noPS|WCE/noPS|CE/PS|WCE/PS|
|---|---|---|---|---|
|A_B1|135 draft|135 draft|95 draft|95 draft|
|B_NARRATIVE|135 draft|135 draft|95 draft|95 draft|
|C_BASELINE_FUSION|89 draft|89 draft|63 draft|63 draft|
|D_P1_r0|114 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|
|E_P2_r0|116 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|
|D_P1_r1_v1|103 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|
|E_P2_r1_v1|103 draft|BLOCKED confidence|BLOCKED confidence|BLOCKED confidence|

## GCN draft masks: primary / matched_all_arms

|Arm|CE/noPS|WCE/noPS|CE/PS|WCE/PS|
|---|---|---|---|---|
|A_B1|89 draft|89 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|B_NARRATIVE|89 draft|89 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|C_BASELINE_FUSION|89 draft|89 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|D_P1_r0|89 draft|89 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|E_P2_r0|89 draft|89 draft|BLOCKED common PS mask|BLOCKED common PS mask|
|D_P1_r1_v1|89 draft|BLOCKED confidence|BLOCKED common PS mask|BLOCKED common PS mask|
|E_P2_r1_v1|89 draft|BLOCKED confidence|BLOCKED common PS mask|BLOCKED common PS mask|

## GCN execution results

Every row is NOT_RUN_BLOCKED: no seed accuracy, Macro-F1, paired delta, mean or SD exists.
Seeds0..9 and30 epochs are planned only. Public-only CI is not real Cora training.

Shared baseline arms are not duplicated across routers.36 unique fit specs /360 planned seed fits after exact deduplication; zero executed.

## Provenance

- source_fusion_sha256: `bc16870399416620ed67f8799ed9bd0f17c2b7cf3c5849b2debe93ac14d96c2c`
- source_outcome_sha256: `ae731ac5c0ade855088e7a18af57ccbb91e4b874af43576c326655f1e57ecf2a`
- source_grid_sha256: `c7f51377905a7d5a224d86ef9342dfdf0430fa1ce518f22ccac6647bf227ca0e`

Raw inputs, node-level GT/outcomes, masks, response bodies and audit receipts are excluded.
See THREE_AGENT_FUSION_GCN.md for the decision table, gates, assumptions and limitations.
