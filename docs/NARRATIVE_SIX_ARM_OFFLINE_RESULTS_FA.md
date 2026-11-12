# تحلیل آفلاین آزمایش شش Prompt در SARA-3

LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT

## روش و حدود اعتبار

هیچ API یا Training جدیدی اجرا نشد. Parser و رأی‌گیری تاریخی بدون تغییر استفاده شدند. فقط سه Sample معتبر امکان رأی دارند؛ یک یا دو Sample معتبر به Prediction تبدیل نشده‌اند. Tie با اولین ظهور در ترتیب Sample حل می‌شود. Confidence رأی‌گیری کالیبره‌شده نیست.
موارد بدون Prediction به‌عنوان Wrong یا Abstention مدل گزارش نشده‌اند. All-target Accuracy برابر Correct/140 و Selective Accuracy برابر Correct/Predicted است. Confusion Matrix هفت ردیف و هشت ستون دارد؛ ستون آخر Unavailable است و در Recall کلاس، False Negative محسوب می‌شود. F1 کلاس بدون پیش‌بینی صفر تعریف شده است.
تحلیل اصلی، اختلاف زوجی B−A روی اشتراک Complete-case است؛ اختلاف روی کل ۱۴۰ نیز جدا ثبت شده است. هیچ رأی‌گیری Partial یا تغییر Prompt پس از GT انجام نشد.

## منشأ و Hashها

Prediction freeze: `aebcd301608c4b27a877c584ced5afde85b66e103e05c2bd5edf569f472fed8e`
Protocol: `a9530d3ee3b2e7cd1bd7813fb11a28ce89b7f7b1c5e1c72cb7f6d096d8535dda`
GT evaluation: `c23a830725122beb7ad2c5380bfb33efe175236d7d3d1f2002337e271dccdb42`
Execution summary: `6cffe5b1bfdae99ef26eefb70dc3fde5c28fb0b37e3bc8bd713c7c4d6751e5fe`

## وضعیت درخواست‌ها

{'AMBIGUOUS_DISPATCH': 1, 'COMPLETED_OUTPUT_INVALID': 4, 'COMPLETED_VALID': 2515}

جزئیات هویت، Receipt، دلیل نامعتبر و Nodeها فقط در Freeze خصوصی نگهداری شده‌اند. مورد Ambiguous فاقد پاسخ ثبت‌شده است؛ هیچ پاسخ جدیدی ساخته یا دوباره درخواست نشد.

## نتایج

|Arm|Correct|Wrong|Unavailable|Coverage %|All-target Accuracy %|Selective Accuracy %|Macro-F1|
|---|---:|---:|---:|---:|---:|---:|---:|
|B1|94|46|0|100.00|67.14|67.14|0.6731|
|v0|103|37|0|100.00|73.57|73.57|0.7355|
|v1-A|97|41|2|98.57|69.29|70.29|0.7116|
|v1-B|91|49|0|100.00|65.00|65.00|0.6490|
|v1-C|95|44|1|99.29|67.86|68.35|0.6786|
|v1-D|94|44|2|98.57|67.14|68.12|0.6761|
|historical_B1|96|44|0|100.00|68.57|68.57|0.6765|
|historical_v0|101|39|0|100.00|72.14|72.14|0.7073|

## مقایسه‌های زوجی

|مقایسه|Common N|Fix|Harm|Delta pp مشترک|Delta pp کل|
|---|---:|---:|---:|---:|---:|
|v1-B_minus_v1-A|138|1|9|-5.797|-4.286|
|v1-A_minus_v0|138|2|6|-2.899|-4.286|
|v1-C_minus_v1-A|137|3|7|-2.920|-1.429|
|v1-D_minus_v1-A|136|2|6|-2.941|-2.143|
|v0_minus_B1|140|11|2|6.429|6.429|
|v1-A_minus_B1|138|7|2|3.623|2.143|
|v1-B_minus_B1|140|1|4|-2.143|-2.143|
|v1-C_minus_B1|139|4|3|0.719|0.714|
|v1-D_minus_B1|138|5|3|1.449|0.000|

## تفسیر توصیفی

بالاترین All-target Accuracy مشاهده‌شده مربوط به v0 است؛ انتخاب پسینی بهترین Arm، شاهد تعمیم یا برتری قطعی نیست.
v0→A هم نمایش و مقدار شواهد را تغییر می‌دهد؛ تغییر آن را نمی‌توان صرفاً به دستورالعمل نسبت داد. A/B/C/D همان شواهد را با دستورهای متفاوت دریافت کردند. مدل با Alias و Revision گزارش‌شدهٔ Provider ثبت شده است؛ مستقل‌بودن مدل زیرین اثبات نشده است. Historical B1/v0 مرجع‌اند و Model-matched با اجرای جدید معرفی نمی‌شوند.

## Homophily، Degree و دادهٔ ناقص

|گروه|N|B1 Correct|v0 Correct|A Correct|B Correct|C Correct|D Correct|
|---|---:|---:|---:|---:|---:|---:|---:|
|homophilic|122|87|95|88|83|86|85|
|mixed|7|1|1|1|1|1|1|
|heterophilic|11|6|7|8|7|8|8|
|isolated|0|0|0|0|0|0|0|
|historical_joint_wrong|38|0|4|2|0|1|1|
|historical_other|102|94|99|95|91|94|93|
|degree_0_0|0|0|0|0|0|0|0|
|degree_1_2|42|27|34|30|27|28|30|
|degree_3_5|71|47|50|49|46|49|47|
|degree_6_10|21|16|15|14|15|15|14|
|degree_11_2707|6|4|4|4|3|3|3|
|provided_neighbors_0|0|0|0|0|0|0|0|
|provided_neighbors_1|19|12|16|14|12|13|15|
|provided_neighbors_2|23|15|18|16|15|15|15|
|provided_neighbors_3|29|19|20|20|20|20|20|
|provided_neighbors_4|69|48|49|47|44|47|44|

Strata توصیفی و پسینی هستند؛ h>0.5 هموفیلیک، h=0.5 مختلط و h<0.5 هتروفیلیک است. Degree از همسایه‌های مستقیم یکتا و بدون Self-loop محاسبه شد. نمونه‌ها وابسته‌اند؛ آزمون معنی‌داری یا ادعای علی انجام نشد.

## هزینه

|Arm|Input tokens|Output tokens|Reasoning tokens|Estimated USD|USD/valid prediction|
|---|---:|---:|---:|---:|---:|
|B1|124422|65814|44476|0.045349|0.000324|
|v0|234996|73944|51882|0.060472|0.000432|
|v1-A|476478|79359|59665|0.087327|0.000633|
|v1-B|494658|101168|82664|0.100050|0.000715|
|v1-C|487518|79245|62017|0.088374|0.000636|
|v1-D|487938|85358|67598|0.091473|0.000663|

نرخ Input=$0.10/M و Output=$0.50/M موقت و تأییدنشده‌اند. Usage پاسخ‌های نامعتبر موجود نیز حساب شده؛ Usage و هزینهٔ درخواست Ambiguous نامعلوم است. Reasoning بخشی از Output است و دوباره حساب نشده است. Actual billed cost نامعلوم است.

## محدودیت و تصمیم بعدی

آزمایش کامل اعلام نمی‌شود؛ تحلیل Strict-partial با Missingness روشن برای پایان‌نامه قابل گزارش است. چهار پاسخ نامعتبر و یک Dispatch نامعلوم تاریخی حفظ شده‌اند. GT فقط پس از Freeze در همین Evaluator باز شد. سه Sample تکرار مستقل پژوهشی نیستند؛ Cora و زیرگروه خطاهای تاریخی قبلاً مشاهده شده‌اند. هیچ Prompt یا آستانه با این نتایج تنظیم نشد.
برای تأیید، پروتکل ازپیش‌ثبت‌شده روی Cohort یا Dataset مستقل و مدل هم‌زمان نیاز است. هر API یا GCN آینده نیازمند مجوز مستقل است. این نتایج هیچ بهبود Downstream GCN را اثبات نمی‌کنند.

جدول‌های Class-wise، Confusion، سه Sample و Strata در reports/six_arm_evaluation_aggregate.json و جزئیات Node-level فقط در .local_artifacts/six_arm_gt_evaluation هستند.

## پاسخ مستقیم به فرضیه‌ها

- بهترین Accuracy توصیفی: Narrative v0 هم‌زمان، 103/140=73.57%. بهترین Macro-F1 نیز v0 با 0.7355 است؛ این انتخاب پسینی برتری تعمیم‌پذیر را اثبات نمی‌کند.
- Multi-neighbor A نسبت به v0 روی 138 مورد مشترک دو اصلاح و شش تخریب داشت؛ Delta=-2.899pp. حتی اگر هر دو Prediction ناموجود A درست بودند، 99/140 کمتر از 103/140 می‌شد؛ بنابراین این افت صرفاً ناشی از Missingness نیست.
- Evidence-guided B نسبت به A روی 138 مورد مشترک یک اصلاح و نه تخریب داشت؛ Delta=-5.797pp. B همهٔ 140 Prediction را دارد؛ Coverage بالاتر باعث نتیجهٔ بهتر نشده است.
- Semantic-consensus C نسبت به A روی 137 مورد مشترک سه اصلاح و هفت تخریب داشت؛ Delta=-2.920pp. Contrastive D روی 136 مورد مشترک دو اصلاح و شش تخریب داشت؛ Delta=-2.941pp. هیچ‌یک در این اجرا بهبود خالص نسبت به A نشان ندادند.
- در 122 هدف هموفیلیک، Correctهای v0/A/B/C/D به‌ترتیب 95/88/83/86/85 بود. در 11 هدف هتروفیلیک، 7/8/7/8/8؛ این نمونهٔ کوچک برای نتیجه‌گیری علّی یا انتخاب Prompt مناسب هر Stratum کافی نیست.
- در 38 خطای مشترک تاریخی، v0 جدید چهار پاسخ درست داشت؛ A دو، B صفر، C و D هرکدام یک. این زیرگروه پسینی است و برای تنظیم Prompt استفاده نشد.
- سه Sample یک تکرار مستقل پژوهشی نیستند. Correctهای تک‌Sample B1 برابر 97/96/93، v0 برابر 101/101/104، A برابر 95/97/98، B برابر 92/92/97، C برابر 95/97/93 و D برابر 97/94/93 هستند. Missingness هر Sample در JSON جدا ثبت است. هیچ Sample بر اساس GT برای جایگزینی رأی تاریخی انتخاب نشد.

## ممیزی پنج مورد حل‌نشده

سه پاسخ HTTP200 در D (دو مورد) و C (یک مورد) فقط دو گزینه داشتند. یک پاسخ HTTP200 در A سه گزینه داشت ولی گزینهٔ سوم خارج از Taxonomy بود. یک Intent دیگر در A هیچ Response ذخیره‌شده‌ای ندارد و Ambiguous باقی ماند. همهٔ چهار پاسخ نامعتبر همچنان REJECTED هستند. هیچ Rejection به COMPLETED تبدیل نشد؛ هیچ درخواست دوباره ارسال نشد. شناسه‌های دقیق، Sample index، Hash و Receipt در فیلد unresolved مربوط به Freeze خصوصی ثبت‌اند. هیچ Response ID تکراری، Intent خارج از Manifest یا مغایرت Integrity یافت نشد.

خلاصهٔ تاریخی فقط Usage مربوط به 2515 پاسخ معتبر را دارد: Input=2300558، Output=484280 و برآورد $0.4721958. با افزودن Usage چهار پاسخ نامعتبر ثبت‌شده، برآورد جمع $0.473045 است؛ مصرف/هزینهٔ Dispatch مبهم همچنان نامعلوم است. این اعداد صورتحساب تأییدشده نیستند.

## بازتولید امن Windows

هیچ API Key لازم نیست. فرمان اجرای API را تکرار نکنید. از ریشهٔ Checkout:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_six_arm_recovery.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.annotation.six_arm_recovery
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.six_arm --freeze aebcd301608c4b27a877c584ced5afde85b66e103e05c2bd5edf569f472fed8e
Get-Content reports\six_arm_metrics.csv
Get-Content reports\six_arm_paired.csv
```

فرمان اول Freeze آفلاین باید همان SHA را بازتولید کند؛ اگر Source/Code/Protocol تغییر کرده است، SHA تازه را با این نتیجه مخلوط نکنید. Evaluator پیش از بازکردن Graph، Receiptها را دوباره تطبیق می‌دهد. گزارش خودکار و JSON/CSV بازتولید می‌شوند؛ تفسیر پژوهشی این سند زیر کنترل Git است. این فرمان‌ها هیچ شبکه، API یا GCN اجرا نمی‌کنند.

## Verification و وضعیت تحویل

Readback مستقل CAS نتیجه، تعدادهای Correct/Covered از Node-level خصوصی، Confusion/F1 و عدم تغییر همهٔ فایل‌های Execution تاریخی PASS شدند. هشت تست Synthetic بازیابی، 16 تست مرتبط Narrative/Runner/Preflight/Homophily و 19 تست Baseline/Voting پاس شدند (43 تست یکتا). اجرای اولیه در Sandbox خطاهای Permission مربوط به Temp/ACL داشت؛ همان تست‌ها با مجوز عادی مالک، بدون تضعیف تست، پاس شدند. Full Suite اجرا نشده و CI راه دور برای این Commit هنوز تأیید نشده است.

API جدید=0؛ Retry=0؛ GCN Training=0. هیچ برتری Downstream ادعا نمی‌شود. توصیهٔ بعدی، گزارش همین نتیجهٔ منفی/خنثی و آزمون مستقل ازپیش‌ثبت‌شده است؛ توسعه یا اجرای جدید در این Slice انجام نمی‌شود.
