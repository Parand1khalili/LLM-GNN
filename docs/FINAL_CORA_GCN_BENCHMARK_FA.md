# بنچمارک نهایی Downstream GCN برای Narrative و SARA-Lite

LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT

## پرسش و روش

هدف مقایسهٔ بردارهای واقعی Frozen با شرایط Training ثابت است؛ هیچ Prompt، Router، Policy، Threshold یا Hyperparameter تغییر نکرد. مجوز مالک شامل اجرای محلی این بنچمارک و پذیرش صریح محدودیت Encoder و Test تاریخی بود. هیچ API یا Cloud GPU استفاده نشد.

ماتریس پیش از Training منجمد شد: ۱۶ Arm، ۱۵ Spec یکتا، ۱۵۰ Fit/Seed مؤثر؛ ۱۱۰ Fit واقعاً جدید و ۴۰ Fit تاریخی با تطبیق کامل Spec/Runtime و Receipt بازاستفاده شدند. Historical Automated V1/R0 دقیقاً Alias بردار Fusion C است؛ ۱۰ Fit تکراری برای این Alias ساخته نشد. هیچ Fit واجد شرایط Pending نیست.

Primary فقط Sensitivity140/Natural/CE/noPS است: Graph اصلی Cora2708، Featureهای 384بعدی، دو لایه GCN با Hidden64، Dropout0.5، Adam با LR0.01 و Weight decay0.0005، ۳۰ Epoch، Seeds0..9، CPU تک‌Thread، بدون L2 normalization، Label smoothing، Validation، Early stopping یا انتخاب بهترین Epoch. Checkpoint آخرین Epoch استفاده شد؛ Seed بر اساس Test انتخاب نشد. Trainer همان downstream/model.py::train_gcn و loop تاریخی است و Trainer دوم ساخته نشد.

## Split، GT و Provenance

Train pool همان ۱۴۰ نود FeatProp منجمد و Test دقیقاً مکمل ۲۵۶۸ نودی آن است. نودهای Abstain/Unavailable از Train حذف می‌شوند ولی وارد Test نمی‌شوند؛ Train و Test جدا هستند. از Split رسمی Planetoid یا Validation جدید استفاده نشد. این پروتکل تاریخی Transductive است: Graph/Feature تمام نودها موجودند، ولی Test GT فقط در Evaluator جدا باز شد.

Loader آموزش فقط Storage32 مربوط به X و Storage1 مربوط به Edge را از فایل SHA-pinned می‌خواند؛ y را باز نمی‌کند و GraphInputs اصلاً فیلد Label ندارد. Plan فقط pseudo-label منجمد دارد. GT برای Router، Admission، Mask، Loss و Weight استفاده نشد. GT پس از Verify و Freeze همهٔ Checkpoint/Logits/Predictionها باز شد.

Hash ذخیرهٔ Graph/Feature و Runtime تأیید شد، اما Receipt تولید Encoder اصلی موجود نیست؛ عدم استفادهٔ تاریخی از GT در ساخت Embedding مستقل اثبات نشده است. مالک این محدودیت را صریحاً برای همین آزمایش پذیرفت. Test قبلاً دیده شده است؛ این بنچمارک Holdout مستقل یا Confirmatory نیست.

Confidence واقعی در Manifest خصوصی با منشأ و null حفظ شد. در CE، Adapter عدد100 را فقط در Slot عددیِ بلااستفادهٔ Backend قرار می‌دهد؛ این Confidence جدید یا احتمال مدل نیست. تمام Loss weightها دقیقاً1 هستند. برای SWITCHهای Lite، Confidence موجود نیست؛ WCE مشترک در قرارداد از ابتدا NOT_SCHEDULED_BLOCKED_COMMON_CONFIDENCE بود. هیچ وزن Missing ساخته یا پس از دیدن CE، WCE برای نجات نتیجه اجرا نشد.

## Hashها

Manifest: `d3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e`

Admission مستقل: `31ee42791d4b02a82eb0a0a400f193cf6184d21ef5dba13f615e3afbcf39921d`

Training verification freeze: `4c022a209098db9f6526b1e399156fdfdb647c43d632d0d5d7e23a2223500e3f`

GT-only result: `bf2f25c1fadc231f8921bd06caf324b52aecccb424d26cb569feaab27e42ee7b`

منشأ Graph/X/Edge، Runtime، Source freezes و Code hashes در reports/final_cora_gcn_provenance.json ثبت شده‌اند؛ IDs، Labelها و Checkpointها فقط خصوصی‌اند.

## جدول اصلی

Accuracy و SD بر حسب درصد/واحد درصد و Macro-F1 در بازه0..1 هستند. SD از نوع Population SD روی ۱۰ Seed است؛ تکرار مستقل Cohort محسوب نمی‌شود. Raw درست/غلط فقط روی Accepted pseudo-labelهاست و GCN Accuracy نیست.

|Arm|Train|Raw درست/غلط|GCN Accuracy ± SD %|Macro-F1 ± SD|
|---|---:|---:|---:|---:|
|current_B1|140|94/46|69.5288 ± 0.3179|0.68673 ± 0.00350|
|current_v0|140|103/37|72.4377 ± 0.5704|0.71035 ± 0.00545|
|current_v1-A|138|97/41|70.5685 ± 0.4675|0.69961 ± 0.00498|
|current_v1-B|140|91/49|66.4097 ± 0.5957|0.66420 ± 0.00496|
|current_v1-C|139|95/44|67.4650 ± 0.4249|0.67020 ± 0.00522|
|current_v1-D|138|94/44|68.4229 ± 0.6563|0.68643 ± 0.00612|
|lite_router_only|103|84/19|74.1005 ± 0.2300|0.72430 ± 0.00287|
|lite|129|96/33|72.9011 ± 0.2592|0.71131 ± 0.00285|
|lite_exact_mask_control|129|96/33|72.5078 ± 0.4491|0.70603 ± 0.00494|
|lite_class_count_control|129|95/34|71.8458 ± 0.4447|0.70260 ± 0.00454|
|historical_A_B1|140|96/44|69.8442 ± 0.4044|0.68976 ± 0.00346|
|historical_B_NARRATIVE|140|101/39|71.7329 ± 0.4586|0.70267 ± 0.00515|
|historical_C_BASELINE_FUSION|93|72/21|72.7765 ± 0.3935|0.71880 ± 0.00434|
|historical_V1_r0|93|72/21|72.7765 ± 0.3935|0.71880 ± 0.00434|
|historical_V1_r1_v1|78|67/11|73.4268 ± 0.3360|0.71763 ± 0.00357|
|historical_Expanded_V1|79|67/12|72.5312 ± 0.4256|0.69131 ± 0.00554|

B1/Narrative تاریخی با برچسب‌های هم‌زمان مخلوط نشدند. Armهای تاریخی با همان Graph/Split/Feature/GCN و CE مقایسه‌پذیرند، ولی تولید LLM آنها هم‌زمان یا Model-matched با Prompt experiment جدید معرفی نمی‌شود.

## کنترل‌ها و اختلاف زوجی

Lite و exact-mask control دقیقاً ۱۲۹ ID یکسان دارند؛ تنها چهار Class متفاوت است. Class-count control نیز ۱۲۹ Label و تعداد کلاس یکسان دارد اما IDs متفاوت‌اند؛ کنترل علیِ دقیق Mask نیست. Router-only ۱۰۳ نود انتخاب‌نشده و Narrative کلاس همان نودها را دارد. مقایسهٔ Naturalهایی با تعداد Label متفاوت، اثر Mask/Coverage و Label را با هم دارد.

|مقایسهٔ Treatment−Reference|Δ Accuracy mean ± SD (pp)|Seed مثبت/صفر/منفی|Δ Macro-F1 mean|
|---|---:|---:|---:|
|lite_minus_lite_exact_mask_control|0.3933 ± 0.3237|9/0/1|0.00528|
|lite_minus_lite_router_only|-1.1994 ± 0.2860|0/0/10|-0.01299|
|lite_minus_lite_class_count_control|1.0553 ± 0.3609|10/0/0|0.00871|
|lite_router_only_minus_current_v0|1.6628 ± 0.5744|10/0/0|0.01395|
|lite_minus_current_v0|0.4634 ± 0.4658|9/0/1|0.00096|
|current_v1-A_minus_current_v0|-1.8692 ± 0.3620|0/0/10|-0.01074|
|current_v1-B_minus_current_v1-A|-4.1589 ± 0.3889|0/0/10|-0.03541|

## پاسخ به پرسش‌های علمی

1. Narrative v0 همچنان بهترینِ شش Prompt هم‌زمان است: GCN=72.4377%. در کل بنچمارک، Router-only با 74.1005% و Macro-F1=0.72430 بهترین میانگین مشاهده‌شده را دارد. بهترین‌بودن پسینی یک Arm، اثبات تعمیم نیست.

2. کیفیت مستقیم LLM و GCN یک معیار نیستند. B1 هم‌زمان فقط94 Correct از140 داشت، درحالی‌که v1-C تعداد95 داشت؛ با این وجود GCN از برچسب‌های B1 به69.5288% و از v1-C به67.4650% رسید. Selective accuracy v1-C نیز بیشتر بود. توزیع کلاس‌ها و محل خطاها در Graph مهم‌اند؛ از این مشاهده علت مشخصی استنباط نمی‌شود.

3. Coverage بیشتر لزوماً بهتر نبود: Router-only با103 Label از Lite با129 و Narrative با140 بهتر شد. اما این مقایسه، اثر مستقل تعداد Label را از انتخاب IDها جدا نمی‌کند. کنترل exact-mask همین جداسازی را برای تغییر Class انجام می‌دهد.

4. Router-only نسبت به Narrative هم‌زمان +1.6628pp Accuracy داشت و هر۱۰ Seed مثبت بود. Macro-F1 میانگین +0.01395 و در۹ Seed مثبت بود. این نتیجه از انتخاب GT-free موجود حاصل شد؛ Router بر اساس نتیجه تنظیم نشد.

5. Lite نسبت به exact-mask no-Agent میانگین +0.3933pp Accuracy و +0.00528 Macro-F1 داشت؛ در۹ Seed مثبت و یک Seed منفی بود. بنابراین برخلاف Net صفر در Raw Correct Count، چهار تغییر Class اثر مثبت کوچک Downstream نشان دادند. این به معنی تضمین اصلاح یا ایمنی Agent نیست.

6. Lite در برابر Router-only میانگین −1.1994pp و در هر۱۰ Seed ضعیف‌تر بود. افزودن26 Label Narrative به Router-only در کنترل D حدود−1.5927pp اثر داشت؛ سپس تغییر چهار Class توسط Lite حدود+0.3933pp از آن را جبران کرد. این تفکیک به همان IDها و همین Cohort محدود است.

7. Lite در برابر Narrative کامل +0.4634pp Accuracy داشت، اما به بهترین راه سادهٔ بدون Agent نرسید. با هزینه و پیچیدگی Reviewer و ۱۰ پاسخ نامعتبر تاریخی، شواهد کافی برای توصیهٔ سیستم Agent به‌جای Router-only نداریم؛ یک اثر محدودِ تغییر Class در Mask ثابت مشاهده شد. هیچ Gate یا Policy جدیدی برای بهترکردن نتیجه ساخته نمی‌شود.

8. مرجع74.376947% مربوط به Automated V1/R1 تاریخی با Sensitivity/Natural/WCE/noPS و78 Label است. با CE تاریخیِ دقیقاً همین بردار، نتیجه73.4268% است. پس اختلاف Router-only CE با مرجع WCE حدود−0.2765pp صرفاً مقایسهٔ توصیفی است و Loss/Weight یکسان نیست. مقایسهٔ CE همسان با Historical V1/R1 برابر+0.6737pp است. WCE تاریخی در گزارش‌های Expanded باقی است؛ هیچ Training آن دوباره اجرا نشد.

## Missingness، Class coverage و محدودیت Agent

شش‌Arm strict-partial حفظ شد: A دو، C یک و D دو unavailable دارند. Lite همان ۱۰ unavailable ناشی از۹ model-identity mismatch و یک Quote نامعتبر و یک abstention را دارد. هیچ موردی با Label دیگر پر نشد. ماسک‌ها و confidence provenance در Manifest خصوصی مستقل از GT ثبت شده‌اند؛ class counts، coverage و raw counts در CSVهای عمومی موجودند. عدم تأیید۹ Alias مدل برای Lite، برآورد ارزش Reviewer را محدود می‌کند و در این بنچمارک تغییر نکرد.

## Verification و منابع

هر۱۵۰ Fit دارای Receipt/Intent سازگار،۳۰ Loss finite، Checkpoint/Logits/Predictions معتبر و Hash صحیح است. Hash پارامترهای اولیه میان Fitهای دارای Seed یکسان برابر بود. هیچ Intent ناقص، Pending، Orphan یا mismatch یافت نشد. Coverage gate این دامنه COMPLETE_VERIFIED است؛ معنی آن کامل‌بودن همین CE benchmark است، نه تکمیل WCE مشترک یا آزمایش LLM ناقص.

۱۱۰ Fit جدید در مجموع99.476 ثانیه داخل Trainer و129.141 ثانیه در کل Runner طول کشیدند؛ CPU یک Thread و GPU خاموش بود. Peak RAM اندازه‌گیری نشده است. مدت Fitهای تاریخی موجود نیست و جعل نشده؛ resource CSV برای آن‌ها null دارد. هیچ API جدید یا هزینهٔ Cloud ایجاد نشد. هزینهٔ قبلی Lite حدود$0.010713 تخمینی بود، نه Billing تأییدشده و نه هزینهٔ این Training محلی.

۳۹ تست مرتبط (Benchmark، Full GCN، Admission و Downstream) اجرا و همگی PASS شدند. Full Suite محلی اجرا نشد. محاسبهٔ مستقل از Confusion، Accuracy/F1 تمام۱۶۰ ردیف Arm/Seed و Readback CAS نتایج PASS شد. هیچ دادهٔ Node-level/Test Prediction یا Checkpoint عمومی نشده است. CI پس از Push بررسی می‌شود؛ تا تأیید آن، موفقیت CI این Commit ادعا نمی‌شود.

## بازتولید امن و توقف

دادهٔ خصوصی و Admission باید محلی موجود باشند. این فرمان‌ها Training را تکرار نمی‌کنند:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_final_benchmark.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.final_benchmark verify --package d3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e --approval 31ee42791d4b02a82eb0a0a400f193cf6184d21ef5dba13f615e3afbcf39921d
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.final_benchmark evaluate --package d3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e --approval 31ee42791d4b02a82eb0a0a400f193cf6184d21ef5dba13f615e3afbcf39921d --training-freeze 4c022a209098db9f6526b1e399156fdfdb647c43d632d0d5d7e23a2223500e3f
.venv\Scripts\python.exe -B scripts\render_final_cora_gcn.py
```

برای ادامهٔ Fitهای ناتمام در یک Recovery واقعی، Runner زیر فقط Fit معتبر موجود را Reuse می‌کند و روی Intent مبهم متوقف می‌شود؛ اکنون همهٔ Fitها کامل‌اند و نیازی به اجرای آن نیست:

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.final_benchmark train --package d3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e --approval 31ee42791d4b02a82eb0a0a400f193cf6184d21ef5dba13f615e3afbcf39921d
```

جداول اصلی، Seedها، اختلاف زوجی، Class-wise PRF، Resource و GraphScope JSON در reports/final_cora_gcn_* هستند. هیچ Result اجرا‌نشده‌ای تولید نشده است. این مرحله آخرین مقایسهٔ برنامه‌ریزی‌شدهٔ Cora بود؛ گام بعدی پایان‌نامه، GraphScope و اعتبارسنجی مستقل CiteSeer با مجوز جداست، نه Variant یا تنظیم تازه روی Cora.
