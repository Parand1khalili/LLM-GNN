# گزارش نهایی Full GCN v1 — ۲۰۲۶-۱۱-۰۸

**LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT**

بسته: `c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413`؛ نتیجهٔ ارزیابی: `7be9973675521a59db735ca21477bd14e8cc2b0d4054323441df992c651d41e9`.
ممیزی ۱۸۷۰ Fit موفق؛ ۳۰ Epoch، Loss متناهی، Hash پارامتر اولیه یکسان در هر Seed، صفر Intent ناقص. ارزیاب جداگانه یک‌بار پس از ممیزی اجرا شد. هیچ Training مجدد یا تغییر Policy انجام نشد.

۶۵۴ سلول معتبر، ۳۰۶ سلول Blocked، ۱۸۷ Spec و ۱۸۷۰ Fit یکتا؛ ۶۵۴۰ ردیف تک‌Seed و ۳۷۷۳ مقایسهٔ زوجی. SD در این گزارش Population SD است. Accuracy برحسب درصد و Macro-F1 در بازهٔ صفر تا یک است.

## Natural: primary / historical_confidence.v1

|Arm|Loss|PS|Train|Accuracy ± SD|Macro-F1 ± SD|
|---|---|---|---:|---:|---:|
|A_B1|ce|False|135|69.6807 ± 0.4118|0.686956 ± 0.003554|
|B_NARRATIVE|ce|False|135|70.9540 ± 0.4126|0.689010 ± 0.005088|
|C_BASELINE_FUSION|ce|False|89|72.4299 ± 0.4467|0.713640 ± 0.005126|
|D_P1_r0|ce|False|114|69.5171 ± 0.6606|0.681533 ± 0.006338|
|E_P2_r0|ce|False|116|69.3925 ± 0.6058|0.680406 ± 0.006037|
|D_P1_r1_v1|ce|False|103|70.6893 ± 0.3391|0.689532 ± 0.003944|
|E_P2_r1_v1|ce|False|103|70.6893 ± 0.3391|0.689532 ± 0.003944|
|A_B1|ce|True|95|70.7360 ± 0.5438|0.698969 ± 0.004431|
|B_NARRATIVE|ce|True|95|71.9120 ± 0.4329|0.710838 ± 0.004411|
|C_BASELINE_FUSION|ce|True|63|71.6238 ± 0.2971|0.705352 ± 0.003053|
|D_P1_r0|ce|True|None|BLOCKED|BLOCKED|
|E_P2_r0|ce|True|None|BLOCKED|BLOCKED|
|D_P1_r1_v1|ce|True|None|BLOCKED|BLOCKED|
|E_P2_r1_v1|ce|True|None|BLOCKED|BLOCKED|
|A_B1|wce|False|135|70.4868 ± 0.3227|0.694427 ± 0.003825|
|B_NARRATIVE|wce|False|135|72.6713 ± 0.5284|0.714872 ± 0.005766|
|C_BASELINE_FUSION|wce|False|89|73.5826 ± 0.3553|0.726961 ± 0.003178|
|D_P1_r0|wce|False|None|BLOCKED|BLOCKED|
|E_P2_r0|wce|False|None|BLOCKED|BLOCKED|
|D_P1_r1_v1|wce|False|None|BLOCKED|BLOCKED|
|E_P2_r1_v1|wce|False|None|BLOCKED|BLOCKED|
|A_B1|wce|True|95|70.0974 ± 0.5976|0.692824 ± 0.005093|
|B_NARRATIVE|wce|True|95|72.0171 ± 0.6096|0.710873 ± 0.006185|
|C_BASELINE_FUSION|wce|True|63|72.9322 ± 0.5324|0.716447 ± 0.004479|
|D_P1_r0|wce|True|None|BLOCKED|BLOCKED|
|E_P2_r0|wce|True|None|BLOCKED|BLOCKED|
|D_P1_r1_v1|wce|True|None|BLOCKED|BLOCKED|
|E_P2_r1_v1|wce|True|None|BLOCKED|BLOCKED|

## Natural: primary / missing_confidence_aware.v1

|Arm|Loss|PS|Train|Accuracy ± SD|Macro-F1 ± SD|
|---|---|---|---:|---:|---:|
|A_B1|ce|False|135|69.6807 ± 0.4118|0.686956 ± 0.003554|
|B_NARRATIVE|ce|False|135|70.9540 ± 0.4126|0.689010 ± 0.005088|
|C_BASELINE_FUSION|ce|False|89|72.4299 ± 0.4467|0.713640 ± 0.005126|
|D_P1_r0|ce|False|114|69.5171 ± 0.6606|0.681533 ± 0.006338|
|E_P2_r0|ce|False|116|69.3925 ± 0.6058|0.680406 ± 0.006037|
|D_P1_r1_v1|ce|False|103|70.6893 ± 0.3391|0.689532 ± 0.003944|
|E_P2_r1_v1|ce|False|103|70.6893 ± 0.3391|0.689532 ± 0.003944|
|A_B1|ce|True|95|70.7360 ± 0.5438|0.698969 ± 0.004431|
|B_NARRATIVE|ce|True|95|71.9120 ± 0.4329|0.710838 ± 0.004411|
|C_BASELINE_FUSION|ce|True|63|71.6238 ± 0.2971|0.705352 ± 0.003053|
|D_P1_r0|ce|True|82|68.1698 ± 0.6246|0.670948 ± 0.004830|
|E_P2_r0|ce|True|84|68.3995 ± 0.6111|0.672582 ± 0.004954|
|D_P1_r1_v1|ce|True|74|70.5685 ± 0.3114|0.691085 ± 0.002633|
|E_P2_r1_v1|ce|True|74|70.5685 ± 0.3114|0.691085 ± 0.002633|
|A_B1|wce|False|135|70.4868 ± 0.3227|0.694427 ± 0.003825|
|B_NARRATIVE|wce|False|135|72.6713 ± 0.5284|0.714872 ± 0.005766|
|C_BASELINE_FUSION|wce|False|89|73.5826 ± 0.3553|0.726961 ± 0.003178|
|D_P1_r0|wce|False|114|69.3653 ± 0.7657|0.682975 ± 0.007578|
|E_P2_r0|wce|False|116|69.0927 ± 0.7507|0.680842 ± 0.007298|
|D_P1_r1_v1|wce|False|103|71.1449 ± 0.4201|0.696861 ± 0.004182|
|E_P2_r1_v1|wce|False|103|71.1449 ± 0.4201|0.696861 ± 0.004182|
|A_B1|wce|True|95|70.0974 ± 0.5976|0.692824 ± 0.005093|
|B_NARRATIVE|wce|True|95|72.0171 ± 0.6096|0.710873 ± 0.006185|
|C_BASELINE_FUSION|wce|True|63|72.9322 ± 0.5324|0.716447 ± 0.004479|
|D_P1_r0|wce|True|82|68.4774 ± 0.4638|0.674789 ± 0.003678|
|E_P2_r0|wce|True|84|68.8084 ± 0.4443|0.677342 ± 0.003154|
|D_P1_r1_v1|wce|True|74|70.7399 ± 0.3964|0.691735 ± 0.004107|
|E_P2_r1_v1|wce|True|74|70.7399 ± 0.3964|0.691735 ± 0.004107|

## Natural: sensitivity / historical_confidence.v1

|Arm|Loss|PS|Train|Accuracy ± SD|Macro-F1 ± SD|
|---|---|---|---:|---:|---:|
|A_B1|ce|False|140|69.8442 ± 0.4044|0.689759 ± 0.003464|
|B_NARRATIVE|ce|False|140|71.7329 ± 0.4586|0.702673 ± 0.005153|
|C_BASELINE_FUSION|ce|False|93|72.7765 ± 0.3935|0.718796 ± 0.004344|
|D_P1_r0|ce|False|118|69.5600 ± 0.6551|0.681988 ± 0.006040|
|E_P2_r0|ce|False|120|69.4120 ± 0.6083|0.680843 ± 0.005661|
|D_P1_r1_v1|ce|False|108|70.9073 ± 0.4242|0.692582 ± 0.004060|
|E_P2_r1_v1|ce|False|108|70.9073 ± 0.4242|0.692582 ± 0.004060|
|A_B1|ce|True|98|71.0241 ± 0.3108|0.702420 ± 0.002875|
|B_NARRATIVE|ce|True|98|71.9743 ± 0.3230|0.712013 ± 0.002999|
|C_BASELINE_FUSION|ce|True|66|72.0016 ± 0.3657|0.710569 ± 0.002903|
|D_P1_r0|ce|True|None|BLOCKED|BLOCKED|
|E_P2_r0|ce|True|None|BLOCKED|BLOCKED|
|D_P1_r1_v1|ce|True|None|BLOCKED|BLOCKED|
|E_P2_r1_v1|ce|True|None|BLOCKED|BLOCKED|
|A_B1|wce|False|140|70.5958 ± 0.3446|0.695964 ± 0.003390|
|B_NARRATIVE|wce|False|140|73.1659 ± 0.4486|0.722161 ± 0.004303|
|C_BASELINE_FUSION|wce|False|93|73.7850 ± 0.3555|0.729913 ± 0.002917|
|D_P1_r0|wce|False|None|BLOCKED|BLOCKED|
|E_P2_r0|wce|False|None|BLOCKED|BLOCKED|
|D_P1_r1_v1|wce|False|None|BLOCKED|BLOCKED|
|E_P2_r1_v1|wce|False|None|BLOCKED|BLOCKED|
|A_B1|wce|True|98|71.4603 ± 0.4034|0.707027 ± 0.003511|
|B_NARRATIVE|wce|True|98|72.3053 ± 0.4829|0.714818 ± 0.004737|
|C_BASELINE_FUSION|wce|True|66|73.6254 ± 0.5402|0.727737 ± 0.005519|
|D_P1_r0|wce|True|None|BLOCKED|BLOCKED|
|E_P2_r0|wce|True|None|BLOCKED|BLOCKED|
|D_P1_r1_v1|wce|True|None|BLOCKED|BLOCKED|
|E_P2_r1_v1|wce|True|None|BLOCKED|BLOCKED|

## Natural: sensitivity / missing_confidence_aware.v1

|Arm|Loss|PS|Train|Accuracy ± SD|Macro-F1 ± SD|
|---|---|---|---:|---:|---:|
|A_B1|ce|False|140|69.8442 ± 0.4044|0.689759 ± 0.003464|
|B_NARRATIVE|ce|False|140|71.7329 ± 0.4586|0.702673 ± 0.005153|
|C_BASELINE_FUSION|ce|False|93|72.7765 ± 0.3935|0.718796 ± 0.004344|
|D_P1_r0|ce|False|118|69.5600 ± 0.6551|0.681988 ± 0.006040|
|E_P2_r0|ce|False|120|69.4120 ± 0.6083|0.680843 ± 0.005661|
|D_P1_r1_v1|ce|False|108|70.9073 ± 0.4242|0.692582 ± 0.004060|
|E_P2_r1_v1|ce|False|108|70.9073 ± 0.4242|0.692582 ± 0.004060|
|A_B1|ce|True|98|71.0241 ± 0.3108|0.702420 ± 0.002875|
|B_NARRATIVE|ce|True|98|71.9743 ± 0.3230|0.712013 ± 0.002999|
|C_BASELINE_FUSION|ce|True|66|72.0016 ± 0.3657|0.710569 ± 0.002903|
|D_P1_r0|ce|True|85|67.9245 ± 0.5044|0.668372 ± 0.004082|
|E_P2_r0|ce|True|87|67.8427 ± 0.6065|0.667888 ± 0.004997|
|D_P1_r1_v1|ce|True|77|71.0397 ± 0.2311|0.695736 ± 0.001911|
|E_P2_r1_v1|ce|True|77|71.0397 ± 0.2311|0.695736 ± 0.001911|
|A_B1|wce|False|140|70.5958 ± 0.3446|0.695964 ± 0.003390|
|B_NARRATIVE|wce|False|140|73.1659 ± 0.4486|0.722161 ± 0.004303|
|C_BASELINE_FUSION|wce|False|93|73.7850 ± 0.3555|0.729913 ± 0.002917|
|D_P1_r0|wce|False|118|69.3341 ± 0.6982|0.682689 ± 0.006907|
|E_P2_r0|wce|False|120|69.0615 ± 0.6700|0.680435 ± 0.006603|
|D_P1_r1_v1|wce|False|108|71.2344 ± 0.4114|0.698165 ± 0.004007|
|E_P2_r1_v1|wce|False|108|71.2344 ± 0.4114|0.698165 ± 0.004007|
|A_B1|wce|True|98|71.4603 ± 0.4034|0.707027 ± 0.003511|
|B_NARRATIVE|wce|True|98|72.3053 ± 0.4829|0.714818 ± 0.004737|
|C_BASELINE_FUSION|wce|True|66|73.6254 ± 0.5402|0.727737 ± 0.005519|
|D_P1_r0|wce|True|85|68.1542 ± 0.4557|0.672067 ± 0.004392|
|E_P2_r0|wce|True|87|68.0218 ± 0.4916|0.670931 ± 0.004378|
|D_P1_r1_v1|wce|True|77|71.3435 ± 0.2885|0.698844 ± 0.002428|
|E_P2_r1_v1|wce|True|77|71.3435 ± 0.2885|0.698844 ± 0.002428|

## اختلاف زوجی Natural: Agent منهای Narrative و Fusion بدون Agent

|Cohort|Protocol|Arm|Loss|PS|Δ Accuracy vs Narrative ± SD|Δ Accuracy vs C ± SD|
|---|---|---|---|---|---:|---:|
|primary|historical_confidence.v1|D_P1_r0|ce|False|-1.4369 ± 0.4648|-2.9128 ± 0.5972|
|primary|historical_confidence.v1|E_P2_r0|ce|False|-1.5615 ± 0.4407|-3.0374 ± 0.5059|
|primary|historical_confidence.v1|D_P1_r1_v1|ce|False|-0.2648 ± 0.1992|-1.7407 ± 0.3743|
|primary|historical_confidence.v1|E_P2_r1_v1|ce|False|-0.2648 ± 0.1992|-1.7407 ± 0.3743|
|primary|missing_confidence_aware.v1|D_P1_r0|ce|False|-1.4369 ± 0.4648|-2.9128 ± 0.5972|
|primary|missing_confidence_aware.v1|E_P2_r0|ce|False|-1.5615 ± 0.4407|-3.0374 ± 0.5059|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|ce|False|-0.2648 ± 0.1992|-1.7407 ± 0.3743|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|ce|False|-0.2648 ± 0.1992|-1.7407 ± 0.3743|
|primary|missing_confidence_aware.v1|D_P1_r0|ce|True|-3.7422 ± 0.6197|-3.4540 ± 0.8105|
|primary|missing_confidence_aware.v1|E_P2_r0|ce|True|-3.5125 ± 0.6594|-3.2243 ± 0.8159|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|ce|True|-1.3435 ± 0.2921|-1.0553 ± 0.3692|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|ce|True|-1.3435 ± 0.2921|-1.0553 ± 0.3692|
|primary|missing_confidence_aware.v1|D_P1_r0|wce|False|-3.3061 ± 0.5495|-4.2173 ± 0.6058|
|primary|missing_confidence_aware.v1|E_P2_r0|wce|False|-3.5787 ± 0.5012|-4.4899 ± 0.5784|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|wce|False|-1.5265 ± 0.2516|-2.4377 ± 0.3493|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|wce|False|-1.5265 ± 0.2516|-2.4377 ± 0.3493|
|primary|missing_confidence_aware.v1|D_P1_r0|wce|True|-3.5397 ± 0.5708|-4.4548 ± 0.5995|
|primary|missing_confidence_aware.v1|E_P2_r0|wce|True|-3.2087 ± 0.5652|-4.1238 ± 0.6253|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|wce|True|-1.2773 ± 0.4666|-2.1924 ± 0.3983|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|wce|True|-1.2773 ± 0.4666|-2.1924 ± 0.3983|
|sensitivity|historical_confidence.v1|D_P1_r0|ce|False|-2.1729 ± 0.4594|-3.2165 ± 0.5280|
|sensitivity|historical_confidence.v1|E_P2_r0|ce|False|-2.3209 ± 0.4657|-3.3645 ± 0.4631|
|sensitivity|historical_confidence.v1|D_P1_r1_v1|ce|False|-0.8255 ± 0.3080|-1.8692 ± 0.4326|
|sensitivity|historical_confidence.v1|E_P2_r1_v1|ce|False|-0.8255 ± 0.3080|-1.8692 ± 0.4326|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|ce|False|-2.1729 ± 0.4594|-3.2165 ± 0.5280|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|ce|False|-2.3209 ± 0.4657|-3.3645 ± 0.4631|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|ce|False|-0.8255 ± 0.3080|-1.8692 ± 0.4326|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|ce|False|-0.8255 ± 0.3080|-1.8692 ± 0.4326|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|ce|True|-4.0498 ± 0.5011|-4.0771 ± 0.6761|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|ce|True|-4.1316 ± 0.6224|-4.1589 ± 0.7871|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|ce|True|-0.9346 ± 0.2196|-0.9618 ± 0.2830|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|ce|True|-0.9346 ± 0.2196|-0.9618 ± 0.2830|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|wce|False|-3.8318 ± 0.4852|-4.4509 ± 0.5773|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|wce|False|-4.1044 ± 0.4382|-4.7235 ± 0.5584|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|wce|False|-1.9315 ± 0.2972|-2.5506 ± 0.3458|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|wce|False|-1.9315 ± 0.2972|-2.5506 ± 0.3458|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|wce|True|-4.1511 ± 0.6277|-5.4712 ± 0.6535|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|wce|True|-4.2835 ± 0.6675|-5.6036 ± 0.6563|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|wce|True|-0.9618 ± 0.3835|-2.2819 ± 0.3616|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|wce|True|-0.9618 ± 0.3835|-2.2819 ± 0.3616|

## اثر PS و WCE در Natural؛ Extension

|Cohort|Arm|PS−noPS در CE|PS−noPS در WCE|WCE−CE بدون PS|WCE−CE با PS|
|---|---|---:|---:|---:|---:|
|primary|A_B1|+1.0553|-0.3894|+0.8061|-0.6386|
|primary|B_NARRATIVE|+0.9579|-0.6542|+1.7173|+0.1051|
|primary|C_BASELINE_FUSION|-0.8061|-0.6503|+1.1526|+1.3084|
|primary|D_P1_r0|-1.3474|-0.8879|-0.1519|+0.3076|
|primary|E_P2_r0|-0.9930|-0.2843|-0.2998|+0.4089|
|primary|D_P1_r1_v1|-0.1207|-0.4050|+0.4556|+0.1713|
|primary|E_P2_r1_v1|-0.1207|-0.4050|+0.4556|+0.1713|
|sensitivity|A_B1|+1.1799|+0.8645|+0.7516|+0.4361|
|sensitivity|B_NARRATIVE|+0.2414|-0.8606|+1.4330|+0.3310|
|sensitivity|C_BASELINE_FUSION|-0.7749|-0.1597|+1.0086|+1.6238|
|sensitivity|D_P1_r0|-1.6355|-1.1799|-0.2259|+0.2298|
|sensitivity|E_P2_r0|-1.5693|-1.0397|-0.3505|+0.1791|
|sensitivity|D_P1_r1_v1|+0.1324|+0.1090|+0.3271|+0.3037|
|sensitivity|E_P2_r1_v1|+0.1324|+0.1090|+0.3271|+0.3037|

## کنترل هم‌تعداد؛ Agent منهای کنترل بدون Agent

|Cohort|Protocol|Arm|Loss|PS|Δ Accuracy ± SD|Δ Macro-F1|
|---|---|---|---|---|---:|---:|
|primary|historical_confidence.v1|D_P1_r0|ce|False|-3.4813 ± 0.5208|-0.035879|
|primary|historical_confidence.v1|E_P2_r0|ce|False|-3.4579 ± 0.4226|-0.035557|
|primary|historical_confidence.v1|D_P1_r1_v1|ce|False|-1.7562 ± 0.3911|-0.020212|
|primary|historical_confidence.v1|E_P2_r1_v1|ce|False|-1.7562 ± 0.3911|-0.020212|
|primary|missing_confidence_aware.v1|D_P1_r0|ce|False|-3.4813 ± 0.5208|-0.035879|
|primary|missing_confidence_aware.v1|E_P2_r0|ce|False|-3.4579 ± 0.4226|-0.035557|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|ce|False|-1.7562 ± 0.3911|-0.020212|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|ce|False|-1.7562 ± 0.3911|-0.020212|
|primary|missing_confidence_aware.v1|D_P1_r0|ce|True|-2.6558 ± 0.3819|-0.029156|
|primary|missing_confidence_aware.v1|E_P2_r0|ce|True|-2.8933 ± 0.4498|-0.031009|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|ce|True|-0.7632 ± 0.4776|-0.013139|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|ce|True|-0.7632 ± 0.4776|-0.013139|
|primary|missing_confidence_aware.v1|D_P1_r0|wce|False|-4.2368 ± 0.4304|-0.044711|
|primary|missing_confidence_aware.v1|E_P2_r0|wce|False|-4.2445 ± 0.4467|-0.044861|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|wce|False|-2.4961 ± 0.3825|-0.030475|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|wce|False|-2.4961 ± 0.3825|-0.030475|
|primary|missing_confidence_aware.v1|D_P1_r0|wce|True|-4.2173 ± 0.2930|-0.045967|
|primary|missing_confidence_aware.v1|E_P2_r0|wce|True|-4.2095 ± 0.3293|-0.045752|
|primary|missing_confidence_aware.v1|D_P1_r1_v1|wce|True|-1.0748 ± 0.5710|-0.018975|
|primary|missing_confidence_aware.v1|E_P2_r1_v1|wce|True|-1.0748 ± 0.5710|-0.018975|
|sensitivity|historical_confidence.v1|D_P1_r0|ce|False|-3.4268 ± 0.5562|-0.036291|
|sensitivity|historical_confidence.v1|E_P2_r0|ce|False|-3.4346 ± 0.3508|-0.036376|
|sensitivity|historical_confidence.v1|D_P1_r1_v1|ce|False|-1.7056 ± 0.4117|-0.021236|
|sensitivity|historical_confidence.v1|E_P2_r1_v1|ce|False|-1.7056 ± 0.4117|-0.021236|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|ce|False|-3.4268 ± 0.5562|-0.036291|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|ce|False|-3.4346 ± 0.3508|-0.036376|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|ce|False|-1.7056 ± 0.4117|-0.021236|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|ce|False|-1.7056 ± 0.4117|-0.021236|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|ce|True|-3.0101 ± 0.5014|-0.032785|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|ce|True|-2.9712 ± 0.5035|-0.032024|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|ce|True|-0.7788 ± 0.2914|-0.013395|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|ce|True|-0.7788 ± 0.2914|-0.013395|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|wce|False|-4.4315 ± 0.4643|-0.047095|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|wce|False|-4.4938 ± 0.4667|-0.048039|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|wce|False|-2.5312 ± 0.3640|-0.031579|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|wce|False|-2.5312 ± 0.3640|-0.031579|
|sensitivity|missing_confidence_aware.v1|D_P1_r0|wce|True|-4.4393 ± 0.4568|-0.047957|
|sensitivity|missing_confidence_aware.v1|E_P2_r0|wce|True|-4.4120 ± 0.4709|-0.047435|
|sensitivity|missing_confidence_aware.v1|D_P1_r1_v1|wce|True|-1.3512 ± 0.3135|-0.022478|
|sensitivity|missing_confidence_aware.v1|E_P2_r1_v1|wce|True|-1.3512 ± 0.3135|-0.022478|

## بهترین سلول‌های مشاهده‌شده؛ نه انتخاب تأییدی

- کل ماتریس / Accuracy: B_NARRATIVE، sensitivity، historical_confidence.v1، wce، PS=True، Mask=pairwise، Pair=['B_NARRATIVE', 'C_BASELINE_FUSION']؛ Accuracy=74.0382 ± 0.4753، Macro-F1=0.732672 ± 0.004535.
- کل ماتریس / Macro-F1: B_NARRATIVE، sensitivity، historical_confidence.v1، wce، PS=False، Mask=pairwise، Pair=['B_NARRATIVE', 'C_BASELINE_FUSION']؛ Accuracy=74.0265 ± 0.2851، Macro-F1=0.732857 ± 0.002162.
- فقط Natural / Accuracy: C_BASELINE_FUSION، sensitivity، historical_confidence.v1، wce، PS=False، Mask=natural، Pair=None؛ Accuracy=73.7850 ± 0.3555، Macro-F1=0.729913 ± 0.002917.
- فقط Natural / Macro-F1: C_BASELINE_FUSION، sensitivity، historical_confidence.v1، wce، PS=False، Mask=natural، Pair=None؛ Accuracy=73.7850 ± 0.3555، Macro-F1=0.729913 ± 0.002917.

## تفسیر و محدودیت‌ها

- Natural: از 40 مقایسهٔ Agent با C، 0 مورد Accuracy مثبت دارند. دامنهٔ Delta برابر -5.6036 تا -0.9618 واحد درصد است.
- کنترل هم‌تعداد: دامنهٔ Delta Accuracy برابر -4.4938 تا -0.7632؛ مثبت در 0 از 40 مورد. این مقایسه تغییر کلاس/وزن را با Coverage ثابت می‌سنجد، نه اثر انتخاب جمعیت.
- PS هم تعداد و هم ترکیب Labelها را تغییر می‌دهد؛ اثر آن علت مستقلِ افزایش یا کاهش کیفیت نیست. WCE روی Mask ثابت اثر وزن‌دهی دارد، ولی مقایسهٔ Maskها و Protocolها ممکن است هم‌زمان ترکیب نمونه را تغییر دهد.
- All-Matched و Pairwise و همهٔ نتایج تک‌Seed در JSON/CSV کامل موجودند. R0 در اشتراک ۸۹/۹۳ نودی با C هم‌کلاس است؛ این Mask اثر Labelهای اضافه را اندازه نمی‌گیرد. دو Router در ۱۷ نود مشترک‌اند و مستقل نیستند.
- هیچ نتیجه‌ای ادعای Independent Replication یا بهبود تعمیم‌پذیر نیست؛ Test تاریخی قبلاً دیده شده و منشأ اجرای Encoder محدود است. جست‌وجوی بهترین سلول Post-hoc و توصیفی است.
- Accuracyهای مقالهٔ ICLR2024 (از جمله PS-FeatProp-W روی Cora برابر 76.23%) فقط مرجع تاریخی‌اند؛ اختلاف Cohort، Labelها، مدل زبانی، Features و Maskها مقایسهٔ مستقیم را نامعتبر می‌کند.
- ممیزی کامل Readback و بررسی تمام Hashها واقعاً اجرا شد. تست واحد/Full Suite جدید یا Training مجدد اجرا نشد؛ کد Frozen تغییر نکرد.

فایل‌ها: `reports/full_gcn_results_v1.csv`، `reports/full_gcn_results_v1.json`؛ داده‌های خصوصی در `.local_artifacts/full_gcn_v1/fits` باقی می‌مانند.