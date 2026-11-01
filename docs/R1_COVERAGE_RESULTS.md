# R1 coverage policy results

Executed2026-11-01, authentic frozen140 sensitivity cohort, budget37 each.
Design and sensitivity settings were recorded in `R1_COVERAGE_POLICY.md` before
new outputs. Recommendation remains v2 for its observed-risk interpretation,
not its HH composition or stability. No prospective pilot is frozen here.

## Primary policies

| Policy | Zero match | Disagreement | HH agreement* | Cutoff score | Score-tied block | Final joint tie |
|---|---:|---:|---:|---|---:|---:|
|Original v1|30|7|15|7/12|2|2|
|Neutral|12|9|16|1/3|62|62|
|Two-dimensional v2|0|6|20|1/3|38|22|

*HH is agreement with both frozen confidence>=80, a reconstructed descriptive
convention, not a recovered historical definition. No correctness is inferred.

Primary intersections: v1/neutral19, v1/v2=7, neutral/v2=25 (out of37).

Ranked selected IDs (all other sensitivity selections and all78 pairwise overlaps
are also recorded in `../reports/r1_coverage_comparison.json`):

Original v1:

`351, 637, 734, 722, 160, 207, 267, 295, 375, 430, 552, 682, 743, 783, 862, 932, 1013, 1031, 1066, 1120, 1269, 1283, 1308, 1776, 1814, 1951, 1958, 2291, 2317, 2327, 2396, 2434, 2490, 2534, 2685, 2698, 130`

Neutral:

`722, 267, 351, 637, 682, 734, 1120, 2291, 2396, 130, 1243, 653, 2319, 2487, 25, 47, 62, 81, 90, 94, 160, 181, 207, 295, 375, 430, 436, 552, 568, 614, 698, 711, 743, 783, 785, 862, 881`

Two-dimensional v2:

`722, 267, 682, 1120, 2291, 2396, 130, 1243, 653, 2319, 2487, 25, 47, 62, 972, 979, 1240, 1260, 1649, 1719, 1764, 1946, 2425, 2695, 81, 90, 94, 181, 436, 568, 614, 698, 711, 785, 881, 917, 1226`

## Prespecified sensitivity

| Policy / setting | Zero match | Disagreement | HH* | Overlap with own primary /37 |
|---|---:|---:|---:|---:|
|v1/wD=1/2|30|5|16|35|
|v1/wD=1|30|7|15|37|
|v1/wD=2|28|9|14|35|
|neutral/wD=1/2|12|8|16|36|
|neutral/wD=1|12|9|16|37|
|neutral/wD=2|12|9|16|37|
|v2/wD=1/2|0|6|20|37|
|v2/wD=1|0|6|20|37|
|v2/wD=2|3|9|18|34|
|neutral/missing=1/4|3|9|16|28|
|neutral/missing=3/4|26|9|15|23|
|v2/coverage=none|3|9|16|33|
|v2/coverage=low|3|9|15|25|

Neutral missing-value choices change many selections: overlaps23..28 versus
its primary. V2 disagreement-weight changes retain34..37; changing coverage tie
priority retains25..33. Large tied score blocks mean tie policy is scientifically
material. Exact risk/coverage ties use ascending node ID; the machine report
includes the entire cutoff block and its selected members. No setting was tuned.

## Coverage and text length

Coverage groups: zero30, partial51, observed multi-keyword59. Mean ASCII-word
counts are118.93,139.51,166.61 respectively (medians110,135,158).
Lengths0..128: zero18/57;129..512: zero11/82;513+: zero1/1.
The longest stratum has only one article and cannot establish a trend.
Primary selected mean lengths: v1=125.73, neutral139.41, v2=154.05.
These associations are compatible with vocabulary/length coverage bias; neither
causation nor class correctness is established. Topic and text availability are
confounders. Repeating tokens or appending words outside the Atlas does not
change coverage/risk in tests, but longer natural texts offer more keyword
opportunities. Existing generic words, inflections, absent synonyms, negation
and auxiliary-method mentions limit interpretation. Atlas was not expanded.

## Verification and limits

Twelve new focused tests and68 relevant regressions PASS (80total,5.002s).
An initial test-harness error treated os.fdopen integer descriptors as paths;
the read-boundary test was corrected and the suite rerun successfully.
Guarded authentic reads allow only nine pinned JSONs plus the public design
document; repeated results and in-memory/file immutability checks pass.
No private human-review files or tests accessed. No GT/provider/training access.
Original v1 selection is checked against its unchanged implementation.
Full repository suite was not run; unrelated L2/runtime/GraphScope untouched.
V2 is implemented separately, not installed as a new runtime default.
Missing evidence still means unknown true risk; absence of positive observed risk
is not evidence of safety. Coverage tie preference is a normative design choice,
not demonstrated optimal routing. No accuracy, L2 or GNN claim is supported.
Next: review the explicit exploitation-versus-unknown-case-exploration objective
and tie priority before freezing a prospective pilot cohort.
