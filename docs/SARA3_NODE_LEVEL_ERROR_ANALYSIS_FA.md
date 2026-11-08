# تحلیل خطای Node-level — SARA-3 — ۲۰۲۶-۱۱-۰۸

**POST_HOC_DIAGNOSTIC / LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT**

این تحلیل روی خروجی‌های قبلاً Frozen است؛ اجرای دوبارهٔ Full GCN Evaluator، Training، Admission یا API نیست. GT فقط در ماژول evaluation/node_diagnostics.py باز شد؛ هیچ خروجی به Router/Policy/Training بازنگشت.

## دامنه و منشأ

- Cohort خام140 و Primary135؛ Test تاریخی GCN برابر2568 گره مجزا از140 گره pseudo-label. مرحلهٔ Raw و Test اهداف متفاوت دارند.
- بستهٔ Full GCN: `c78ff16df921bfcd661ce7981c5467f31c243bd812466ce0bbca747be576d413`؛ Expanded: `789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83`؛ Feature: `e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`.
- Graph/GT: `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`؛ قبل از decode، بایت و ترتیب نام کلاس‌ها با Receipt اصلی تطبیق داده شد.
- شناسهٔ هر روش، prediction_sha256 و Source Hash در method_sources فایل Aggregate ثبت شده است. A/B/C از sara.three_agent.fusion.v1؛ V1=sara.arbitration.automated_concordance.v1؛ V2=sara.arbitration.weighted.v2؛ Direct=sara.arbitration.weighted.v2.direct_seed.v1؛ V3=sara.arbitration.evidence.v3؛ Consensus=sara.ablation.consensus_only.v1؛ P1/P2=sara.fusion.conservative.v1 / sara.fusion.relaxed.v1.
- Blind/Comparison از rich_evidence.v1، rich_prompt.v2 و Gateway4096 احراز‌شدهٔ R0/R1-v1 هستند. Legacy ناقص، Judge002 گمشده و Syntheticها به‌عنوان پاسخ واقعی کامل اضافه نشدند. Routerهای دیگر پاسخ کامل Router-bound ندارند؛ Accuracy آن‌ها ساخته نشد.
- V1/V2/Direct/V3/Consensus تنها بازسازی Raw هستند؛ به‌جز بردارهای واقعاً برابر با Arm قدیمی، GCN جدیدی برای آن‌ها اجرا نشده است. تساوی بردار به‌تنهایی مجوز ادعای اجرای تازه نیست.

## تعریف‌ها

- CORRECT/WRONG فقط برای کلاس معتبر؛ ABSTAIN برچسب null در پاسخ موجود؛ MISSING شامل پاسخ Rejected/غیرمجاز/Not-routed است و در دادهٔ خصوصی با state اصلی قابل تفکیک است. هیچ Missing به Abstain یا Wrong تبدیل نشد.
- Coverage=accepted/تمام Cohort؛ Selective Accuracy=correct/accepted. Confusion دارای7 سطر GT و9 ستون (هفت کلاس،ABSTAIN،MISSING) است.
- Class Precision=TP/(TP+FP). Recall_observed=TP/(GT support بدون Missing) و Abstain در FN؛ Recall_all تمام GT support را مخرج می‌گیرد. F1_observed با همین تعریف است. نبود support یا پیش‌بینی کلاس به0 تبدیل شده و support جدا ثبت شده است.
- Pairwise روی Universe مشترک گزارش می‌شود؛ Common Accepted فقط دو کلاس موجود را مقایسه می‌کند. Jaccard Error فقط WRONGهای واقعی است؛ union خالی=null، نه توافق ساختگی.
- Fix=WRONG→CORRECT؛ Harm=CORRECT→WRONG. حذف Correct به Abstain جداست؛ ABSTAIN→CORRECT افزودن Label است، نه اصلاح خطای قبلی.

## تمام روش‌های Raw؛ Sensitivity140

|روش|Correct|Wrong|Abstain|Missing|Coverage %|Selective Accuracy %|
|---|---:|---:|---:|---:|---:|---:|
|A_B1|96|44|0|0|100.00|68.57|
|B_NARRATIVE|101|39|0|0|100.00|72.14|
|CONSENSUS_r0|101|39|0|0|100.00|72.14|
|CONSENSUS_r1_v1|101|39|0|0|100.00|72.14|
|C_BASELINE_FUSION|72|21|47|0|66.43|77.42|
|D_P1_r0|88|30|22|0|84.29|74.58|
|D_P1_r1_v1|82|26|32|0|77.14|75.93|
|E_P2_r0|89|31|20|0|85.71|74.17|
|E_P2_r1_v1|82|26|32|0|77.14|75.93|
|V1_r0|72|21|47|0|66.43|77.42|
|V1_r1_v1|67|11|62|0|55.71|85.90|
|V2_DIRECT_r0|101|39|0|0|100.00|72.14|
|V2_DIRECT_r1_v1|101|39|0|0|100.00|72.14|
|V2_r0|101|39|0|0|100.00|72.14|
|V2_r1_v1|101|39|0|0|100.00|72.14|
|V3_r0|101|39|0|0|100.00|72.14|
|V3_r1_v1|101|39|0|0|100.00|72.14|
|r0_blind|19|11|7|103|21.43|63.33|
|r0_compare|17|10|2|111|19.29|62.96|
|r1_v1_blind|17|8|12|103|17.86|68.00|
|r1_v1_compare|15|9|0|116|17.14|62.50|

برای Phaseها، Missing بیشتر شامل خارج Router بودن است: Blindها37 مشاهده دارند؛ R0 هفت و R1 دوازده Abstain. Comparison در R0 تعداد29 Completed (دو Abstain)، در R1 تعداد24 Completed دارد. Rejection و Comparison ممنوع پس از Blind-Abstain، موجودیت Prediction ندارند.

## اشتراک و اصلاح/تخریب

|A → B|Both Correct|Both Wrong|Fix|Harm|Correct→Abstain|Wrong→Abstain|Common Accepted|Jaccard Correct|Jaccard Error|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A_B1 → B_NARRATIVE|95|38|6|1|0|0|140|0.9314|0.8444|
|A_B1 → CONSENSUS_r0|94|37|7|2|0|0|140|0.9126|0.8043|
|A_B1 → CONSENSUS_r1_v1|95|38|6|1|0|0|140|0.9314|0.8444|
|A_B1 → C_BASELINE_FUSION|72|21|0|0|24|23|93|0.75|0.4773|
|A_B1 → D_P1_r0|83|28|5|2|11|11|118|0.8218|0.6087|
|A_B1 → D_P1_r1_v1|79|25|3|1|16|16|108|0.798|0.5556|
|A_B1 → E_P2_r0|84|29|5|2|10|10|120|0.8317|0.6304|
|A_B1 → E_P2_r1_v1|79|25|3|1|16|16|108|0.798|0.5556|
|A_B1 → V1_r1_v1|67|11|0|0|29|33|78|0.6979|0.25|
|A_B1 → r0_blind|11|7|8|4|1|6|30|0.1058|0.1458|
|A_B1 → r1_v1_blind|13|7|4|1|0|12|25|0.13|0.1556|
|B_NARRATIVE → CONSENSUS_r0|97|35|4|4|0|0|140|0.9238|0.814|
|B_NARRATIVE → CONSENSUS_r1_v1|99|37|2|2|0|0|140|0.9612|0.9024|
|B_NARRATIVE → C_BASELINE_FUSION|72|21|0|0|29|18|93|0.7129|0.5385|
|B_NARRATIVE → D_P1_r0|84|26|4|4|13|9|118|0.8|0.6047|
|B_NARRATIVE → D_P1_r1_v1|80|24|2|2|19|13|108|0.7767|0.5854|
|B_NARRATIVE → E_P2_r0|85|27|4|4|12|8|120|0.8095|0.6279|
|B_NARRATIVE → E_P2_r1_v1|80|24|2|2|19|13|108|0.7767|0.5854|
|B_NARRATIVE → V1_r1_v1|67|11|0|0|34|28|78|0.6634|0.2821|
|B_NARRATIVE → r0_blind|12|5|7|6|3|4|30|0.1111|0.1111|
|B_NARRATIVE → r1_v1_blind|14|6|3|2|1|11|25|0.1346|0.1463|
|C_BASELINE_FUSION → D_P1_r0|72|21|0|0|0|0|93|0.8182|0.7|
|C_BASELINE_FUSION → D_P1_r1_v1|72|20|1|0|0|0|93|0.878|0.7407|
|C_BASELINE_FUSION → E_P2_r0|72|21|0|0|0|0|93|0.809|0.6774|
|C_BASELINE_FUSION → E_P2_r1_v1|72|20|1|0|0|0|93|0.878|0.7407|
|C_BASELINE_FUSION → V1_r1_v1|67|11|0|0|5|10|78|0.9306|0.5238|
|C_BASELINE_FUSION → r0_blind|0|0|0|0|0|0|0|0.0|0.0|
|C_BASELINE_FUSION → r1_v1_blind|5|2|1|0|0|7|8|0.0595|0.0741|

- B1 و Narrative روی95 گره مشترکاً درست، روی38 گره هر دو غلط‌اند؛ از این38،36 گره کلاس غلط یکسان دارند. شش گره B1 غلط/Narrative درست و یک گره برعکس است. اشتراک زیاد خطا نشان می‌دهد دو Prompt یک LLM، Committee مستقل نیستند.
- C از38 خطای مشترک17 مورد را حذف می‌کند و21 مورد را نگه می‌دارد. نسبت به Narrative،18 خطا و29 پیش‌بینی درست را حذف می‌کند؛ حذف نمونه‌ها را اصلاح کلاس نمی‌نامیم.
- Consensus نسبت به Narrative در R0 چهار Fix/چهار Harm و R1 دو Fix/دو Harm دارد؛ هر دو Net صفر. Weighted V2/Direct/V3 بدون Switch هستند و دقیقاً بردار Narrative را حفظ می‌کنند؛ P1/P2 در R1 یکسان‌اند.
- در C→P1-R0،16 Label صحیح و9 غلط اضافه می‌شود، ولی21 خطای موجود C دست‌نخورده‌اند. P2-R0،17 صحیح و10 غلط اضافه می‌کند. در R1،9 صحیح و6 غلط اضافه و یک خطای C اصلاح می‌شود؛ تعداد Label به‌تنهایی کیفیت را نشان نمی‌دهد.

## Class-wise

ترتیب کلاس‌ها:0 rule_learning،1 neural_networks،2 case_based،3 genetic_algorithms،4 theory،5 reinforcement_learning،6 probabilistic_methods. جدول کامل Precision/Recall/F1 و support برای21 روش و دو Cohort در reports/sara3_raw_classwise_v1.csv است. Confusion کامل در JSON Aggregate قرار دارد. نمونهٔ F1_observed در Sensitivity:

|Class|B1|Narrative|C|P1 R0|P2 R0|P1 R1|
|---|---:|---:|---:|---:|---:|---:|
|0|0.5556|0.5556|0.6250|0.5000|0.5000|0.5000|
|1|0.7532|0.8000|0.6377|0.7200|0.7368|0.6849|
|2|0.8235|0.8485|0.7742|0.8485|0.8485|0.8125|
|3|0.8462|0.8462|0.7273|0.8000|0.8000|0.7273|
|4|0.4000|0.4800|0.1875|0.2778|0.2703|0.3429|
|5|0.6154|0.6667|0.7273|0.7692|0.7692|0.7273|
|6|0.7419|0.7541|0.6923|0.7857|0.7857|0.7636|

## Router و Atlas

|Router|Selected any-error|Unselected any-error|Error enrichment|No-Atlas selected: errors/count|Atlas-observed selected|
|---|---:|---:|---:|---:|---:|
|r0|22/37|23/103|2.663|9/11|13/26|
|r1_v1|24/37|21/103|3.181|20/30|4/7|

- R0-only و R1-only هرکدام20 گره و اشتراک17 گره است. این گروه‌ها مستقل نیستند. فهرست IDها فقط خصوصی است.
- میان Selectedها، Narrative در R0 روی16 و در R1 روی20 گره غلط است؛ Blind به‌ترتیب7 و3 مورد را درست پاسخ داده است. میان گره‌هایی که هر دو Baseline غلط‌اند، حداقل یکی از Phaseهای معتبر روی6 گره R0 و2 گره R1 کلاس صحیح داشته است. این «قابلیت اصلاح مشاهده‌شده» است، نه توان بالقوهٔ تضمین‌شده یا Admission.
- در R1-v1 هر30 گره بدون Atlas match انتخاب شده‌اند؛20 خطادار و10 دارای هر دو Baseline صحیح‌اند. نرخ20/30 با4/7 گروه دارای Match مقایسهٔ بسیار کوچک و انتخاب‌شده است؛ نبود Keyword اثبات اشتباه نیست. در کل Cohort نیز absence و error هم‌بستگی دارند، اما علتِ واژگان، طول متن و خطا از این مشاهده جدا نمی‌شود.
- Phase agreement: R0 تعداد25 توافق کلاسی،2 اختلاف و10 ناموجود/Abstain؛ R1 تعداد23 توافق،1 اختلاف و13 ناموجود/Abstain. توافق دو فاز، شاهد مستقل نیست.
- از16 کاندیدای تغییرِ Consensus، هر16 Warning و Counter-evidence دارند؛ فقط11 Shared Quote و یک برابری لفظی Topic. این ثابت‌بودن flags برای تفکیک Fix/Harm مفید نیست؛ معنای هشدارها مستقلاً تأیید نشده است.
- Third-class نهایی: R0 هفت مورد (3 صحیح/4 غلط)، R1 چهار مورد (1 صحیح/3 غلط). این خروجی آزمایشی است، نه Admission تازه یا L2 PASS.

## خطاهای Downstream، Seed-paired

تنظیم‌های ثابت پیش از decode GT: فقط Primary و Extension؛ Natural CE/noPS، Natural WCE/noPS، Natural CE/PS، All-Matched CE/noPS و Coverage-control CE/noPS. مجموع32 ردیف،22 Spec یکتا؛ Checkpointها بازخوانی شدند، هیچ Fit اجرا نشد.
Always Correct=درهر10 Seed درست؛ Always Wrong=درهر10 غلط؛ Seed-dependent=بین1 تا9 Seed درست. این‌ها دو Cohort مستقل نیستند و نوسان Seed عدم‌قطعیت داده را اندازه نمی‌گیرد.

|Natural Primary CE/noPS|Always Correct|Always Wrong|Seed-dependent|
|---|---:|---:|---:|
|A_B1|1691|694|183|
|B_NARRATIVE|1720|663|185|
|C_BASELINE_FUSION|1797|634|137|
|D_P1_r0|1699|694|175|
|E_P2_r0|1697|698|173|
|D_P1_r1_v1|1738|685|145|
|E_P2_r1_v1|1738|685|145|

|GCN A → B، Natural Primary CE/noPS|میانگین Fix نود Test در هر Seed|میانگین Harm|Net|
|---|---:|---:|---:|
|A_B1 → B_NARRATIVE|111.2|78.5|+32.7|
|A_B1 → C_BASELINE_FUSION|166.1|95.5|+70.6|
|A_B1 → D_P1_r0|139.2|143.4|-4.2|
|A_B1 → E_P2_r0|133.3|140.7|-7.4|
|A_B1 → D_P1_r1_v1|129.8|103.9|+25.9|
|A_B1 → E_P2_r1_v1|129.8|103.9|+25.9|
|B_NARRATIVE → C_BASELINE_FUSION|138.0|100.1|+37.9|
|B_NARRATIVE → D_P1_r0|113.9|150.8|-36.9|
|B_NARRATIVE → E_P2_r0|108.1|148.2|-40.1|
|B_NARRATIVE → D_P1_r1_v1|103.7|110.5|-6.8|
|B_NARRATIVE → E_P2_r1_v1|103.7|110.5|-6.8|
|C_BASELINE_FUSION → D_P1_r0|52.8|127.6|-74.8|
|C_BASELINE_FUSION → E_P2_r0|54.5|132.5|-78.0|
|C_BASELINE_FUSION → D_P1_r1_v1|50.3|95.0|-44.7|
|C_BASELINE_FUSION → E_P2_r1_v1|50.3|95.0|-44.7|

همهٔ Seedها، حالت‌های اشتراک/Jaccard و رویدادهای زوجی در JSON Aggregate و فایل خصوصی موجودند. Exact-ID coverage control اثر Coverage را ثابت نگه می‌دارد؛ در WCE وزن‌ها نیز ممکن است تغییر کنند. از این آزمایش نمی‌توان نسبت داد که یک Label آموزشی خاص علت یک خطای Test خاص بوده است.

## فایل‌ها و Verification

- گزارش Aggregate: reports/sara3_node_diagnostics_v1.json؛ تمام Pairها: reports/sara3_raw_pairwise_v1.csv؛ Class-wise: reports/sara3_raw_classwise_v1.csv؛ گروه‌های شمارشی/Third-class: reports/sara3_node_groups_summary_v1.json.
- جدول خصوصی قابل بازکردن: `.local_artifacts/node_diagnostics_v1/raw_node_table_private.csv`؛ فهرست دقیق Nodeهای Fix/Harm و اشتراک: `.local_artifacts/node_diagnostics_v1/private_node_groups.json`.
- فایل خصوصی کامل شامل Test Predictions و رویدادهای تمام Seedها: `.local_artifacts/node_diagnostics_v1/03cf38ffb395abe24a963b7d5e7c0cb39a8a0d50e85955ef3be91d4974416f65.json`؛ شناسه‌های GCN row_id از Aggregate به آن متصل می‌شوند.
- Hash خلاصهٔ اولیهٔ Diagnostic: `912aaa41c33c2995eadd36eda4557031aee3a63bb31a623af1be0299dc778b3a`. گزارش گروه‌ها derivative جداست؛ artifactهای قبلی تغییر نکردند.
- Synthetic self-check: جدایی Missing/Abstain، Common Mask و Confusion PASS. مقایسه‌های واقعی همان خروجی‌های Frozen هستند؛ Full Suite/CI یا Training جدید اجرا نشد. فایل‌های خصوصی، GT و Node Predictions Commit/Push نمی‌شوند.
- دو تست متمرکز Synthetic در `test_node_diagnostics.py` نیز PASS شدند: تفکیک Missing/Abstain و جلوگیری از ورود کلاس خارج دامنه به ستون Abstain. این Guard فقط ابزار Diagnostic جدید را پوشش می‌دهد؛ داده‌های معتبر یا Ruleهای Frozen تغییر نکردند. Full Suite/CI جدید اجرا نشد.
