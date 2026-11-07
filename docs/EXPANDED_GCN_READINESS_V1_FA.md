# آمادگی آزمایش جامع Router / Arbitration / Fusion — ۲۰۲۶-۱۱-۰۸

فقط Inventory، بازسازی GT-free و برنامه‌ریزی؛ صفر Admission، API، Training و
GT Evaluation جدید. نتایج Full GCN v1، فایل‌های خصوصی قبلی و تغییرات کاربر حفظ شدند.
`LIMITED_PROVENANCE_EXPLORATORY` و `EXPLORATORY_NOT_INDEPENDENT` برقرارند.
برای انتخاب Arm هیچ Outcome GT-only جدیدی خوانده نشد؛ Ruleها از ماژول‌های Frozen
فراخوانی شدند. اطلاعات نتیجهٔ قبلی در Project State مبنای تنظیم Rule نبود.

## Router و پوشش واقعی

|Router|Blind معتبر کامل|Comparison کامل /Rejected|بدون Comparison به‌علت Abstention|گره فاقد پاسخ سازگار Rich4096|وضعیت|
|---|---:|---:|---:|---:|---|
|R0|37|29 /1|7|0|بازسازی با حفظ Rejection|
|R1-v1|37|24 /1|12|0|بازسازی با حفظ Rejection|
|Semantic-v0|0|0|نامعلوم|11|Blocked؛ پاسخ Router-bound موجود نیست|
|R1-v2|0|0|نامعلوم|21|Blocked؛ پاسخ Router-bound موجود نیست|
|R2-v1|0|0|نامعلوم|6|Blocked؛ پاسخ Router-bound موجود نیست|
|R1-neutral-v1؛ Ablation پیاده‌سازی‌شده|0|0|نامعلوم|11|Blocked؛ پاسخ Router-bound موجود نیست|

این صفرها به معنی «هیچ فایل تاریخی برای Node وجود ندارد» نیستند؛ به معنی نبود
مجموعهٔ احراز‌شده برای همان Router/قرارداد هستند. انتخاب هر Router با کد فعلی و
کلاس‌های Frozen، بدون GT محاسبه شد. Union انتخاب Routerهای Blocked برابر66 گره
و148 جایگاه Router-node است؛23 گره یکتا خارج از57 گره دارای پاسخ Rich4096 معتبرند.
این23 گره برای تکمیل این پروتکل به تولید پاسخ جدید نیاز دارند، نه Confidence جعلی.
43 گره مشترکِ دیگر تنها پس از اثبات برابری کامل Request/Dependency/Context و یک
قاعدهٔ بدون GT برای منشأ پاسخ قابل استفاده‌اند؛ صرف Node ID مشترک کافی نیست.
تعداد دقیق API پس از این بررسی و تعیین Comparisonهای شرطی مشخص می‌شود؛ نه23 و
نه148 را تعداد قطعی Generation معرفی نمی‌کنیم. فعلاً هیچ مجوز API صادر نشده است.

دو Rejection موجود پاسخ معتبر محسوب نشدند، اما Receipt معتبرِ شکست دارند. بازسازی
نتیجهٔ واقعی شامل همین Failure و Fallback ازپیش‌تعریف‌شده است؛ آن‌ها missing-file
نیستند و بدون Amendment/مجوز جایگزین نمی‌شوند.

## نسخه‌های Agent و شواهد

- Rich schema `sara.verifier.rich_evidence.v1` با Prompt
  `sara.verifier.rich_prompt.v2` و Gateway4096: برای R0/R1-v1،129 Intent واقعی
  از Journal اصلی و Continuation بازخوانی شد؛74 Blind و53 Comparison کامل، دو
  Comparison ردشده. Receipt، Request identity، Context، Dependency، raw hash و L1
  با `correction_features.extract_run` دوباره تطبیق داده شدند؛ خروجی با Feature
  Freeze به SHA `e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe`
  دقیقاً برابر بود. تغییر Router پاسخ تصادفی جدیدی تولید نکرد.
- اجرای Rich Prompt V2 با سقف512 توکن، Journal مجزای یک Intent دارد؛ مجموعهٔ37
  گره نیست و سقف/Execution Context آن معادل4096 نیست. **Blocked** برای Matrix
  کامل این نسخه؛ خروجی محدود به‌جای پاسخ کامل جایگزین نشد.
- Canaryها و پایلوت Legacy شش‌گرهی در Ledgerهای اصلی Catalog شدند؛ شکست endpoint،
  identity، blind-only و amendmentها با Gateway4096 ادغام نشدند. برخی Ledgerهای
  قدیمی در جدول intents فقط state دارند؛ از این Catalog هیچ Class/Node Mapping
  حدس زده نشد. برای مطالعهٔ مستقل Legacy، Adapter/Mapping احراز‌شده و پوشش کامل
  قرارداد لازم است؛ **Blocked**، نه ادعای بازیابی کامل یا نبود فایل.
- Historical P0/Judge002: انتخاب منطقی تاریخی با Wire/Prompt اجراییِ بازیابی‌شده
  یکسان نیست. فایل‌های Codex-era گمشده به‌عنوان Source بازیابی‌شده معرفی نشدند؛
  **MISSING_EVIDENCE** برای Arm کامل Judge002/Policy002 تاریخی. policy.py فعلی
  صریحاً Policy002 بازسازی‌شده است، نه معادل تاریخی اثبات‌شده.
- Verifierهای Synthetic، شش Development Case و L2 انسانی، پاسخ واقعی Agent3
  برای این آزمایش نیستند؛ وارد Arm یا Inventory پاسخ احراز‌شده نشدند.

## Armهای قابل بازسازی؛ بدون ساخت Policy جدید

|Policy|R0 /R1-v1 قابل بازسازی؟|تعداد Label در Sensitivity140|نکته|
|---|---|---|---|
|A B1 / B Narrative / C Baseline Fusion|بله، مشترک|140 /140 /93|Baselineها تکراری اجرا نمی‌شوند|
|Automated Concordance V1|بله|93 /78|Routed بدون Proposal، Abstain؛ Unrouted Agreement80 حفظ می‌شود|
|Weighted V2|بله|140 /140|صفر Switch؛ دقیقاً Narrative با Confidence اصلی|
|V2 Direct-seed Variant|بله|140 /140|صفر Switch؛ دقیقاً Narrative|
|Evidence-only V3|بله|140 /140|صفر Switch؛ دقیقاً Narrative|
|Consensus-only Diagnostic Ablation|بله|140 /140|پیش‌فرض Narrative؛ Switchهای GT-free ده /شش؛ نه تأیید Admission|
|Conservative Fusion P1|بله|118 /108|همان بردار منجمد Full GCN v1|
|Relaxed Fusion P2|بله|120 /108|P1/P2 در R1 یکسان؛ در R0 متفاوت|

برای چهار Router بدون مجموعهٔ پاسخ کامل، هر هفت مسیر Policy بالا **28 ترکیب
Router-policy مسدود** دارند؛ آن‌ها در تعداد Fitهای قابل آماده‌سازی گنجانده نشدند.
این Block با تنظیم Threshold یا انتقال بی‌پروانهٔ پاسخ رفع نشده است.

17 نام Arm،9 بردار یکتای Class/Confidence/Abstention و سه بردار جدید نسبت به
Full GCN v1 وجود دارد. Equivalenceهای کامل:

- Narrative = V2-R0/R1 = Direct-R0/R1 = V3-R0/R1.
- V1-R0 = C، با همان Confidence و Mask؛ Zero Proposal پنهان نشده است.
- P1-R1 = P2-R1.
- V1-R1 و دو Consensus بومی بردارهای تازه‌اند.

V1 با V2/V3 یک Fallback ندارد: V1 Routed را Abstain می‌کند؛ V2/V3 به‌صورت بومی
Narrative را پیش‌فرض دارند. این‌ها با یکدیگر یا با P1/P2 جایگزین نشدند. Confidence
برچسب نگه‌داشته‌شده، Confidence واقعی Narrative باقی می‌ماند؛ Switch فقط از منبع
Baseline منطبق Confidence می‌گیرد، و Third-class ناموجود/null است. همهٔ Labelها
`training_eligible=false` هستند. اطلاعات Node-level فقط در بستهٔ خصوصی است.

## Matrix و بودجه

5232 ردیف برای Armهای قابل بازسازی: CE/WCE، PS/noPS، Primary/Sensitivity، دو
Confidence Protocol، Natural، Expanded-All-Matched، تمام زوج‌های Matched و
Coverage-matched no-Agent. All-Matched و Coverage Controlهای اصلی v1 نیز عیناً
حفظ شدند؛ اشتراک توسعه‌یافته جایگزین اشتراک89/93 قبلی نیست.

4044 ردیف از نظر داده Draft هستند؛72 به‌علت Missing Confidence و1116 به‌علت
Common Mask نامشخص Blocked‌اند. این اعداد ردیف‌اند، نه Fit مستقل یا نتیجهٔ علمی.
همهٔ معیارهای اجرا‌نشده خالی‌اند. PS/WCE از helperهای Frozen موجود فراخوانی شدند؛
Missing-confidence extension هرگز به‌عنوان پروتکل تاریخی معرفی نشده است.

Controls هم‌تعداد، Train IDs پس از PS هر Treatment را حفظ می‌کنند، کلاس را فقط با
قاعدهٔ قبلیِ توافق Baseline/Confidence بالاتر/Hash تساوی انتخاب می‌کنند و دوباره
PS اجرا نمی‌کنند. بودجهٔ PS کنترل از PS موروثی Treatment جدا ثبت شده است.

|کار محاسباتی|تعداد|
|---|---:|
|Specهای یکتا با Graph/IDs/Classes/Weights/Config/Runtime دقیق|359|
|Specهای منطبق با Full GCN v1 و Receipt بازخوانی‌شده|187|
|Fitهای Seedدار قابل بازاستفاده، بدون آموزش مجدد|1870|
|Specهای جدید|172|
|Fitهای جدیدِ لازم با Seeds0..9|1720|
|Fit/API/Admission جدید اجرا‌شده در این Slice|0|

برآورد صرفاً برنامه‌ریزی با نرخ مشاهده‌شدهٔ قبلی3856s/1870fit، حدود59 دقیقه برای
Training جدید است؛ تضمین زمان نیست و هزینهٔ Audit/IO و نوسان سیستم را پوشش نمی‌دهد.
دامنهٔ Routerهای Blocked در این بودجه نیست؛ بدون پاسخ واقعی، Label/Mask/Weights
و تعداد Specهای آن‌ها قابل تعیین نیست. هیچ هزینهٔ API یا Token Count اختراع نشد.

## مسیرها، Hash و بررسی‌های واقعی

- ابزار: `src/llmgnn_sara/downstream/expanded_inventory.py`؛ فقط Prepare، بدون
  ورودی Credential، Evaluator یا مسیر Training. اجرای Owner-local با
  `.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.expanded_inventory`.
- بستهٔ خصوصی نهایی: `.local_artifacts/expanded_gcn_inventory_v1/789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83.json`.
  Class/Confidence/Abstention/Source همهٔ Armها، Source bindings، Catalog قدیمی،
  ماتریس و Specها در آن است؛ به Git اضافه نشود.
- `reports/expanded_gcn_readiness_v1.json`: خلاصهٔ غیرحساس؛
  `reports/expanded_gcn_matrix_v1.csv`: همهٔ5232 ردیف برنامه، بدون Node Label/GT.
- بازسازی مستقیم V2 و Direct/V3/Consensus از ماژول اصلی؛ تطبیق پاسخ‌های احراز‌شده
  با Freeze؛ تطابق کامل187 Spec و بازخوانی Checkpoint/Receipt هر ده Seed انجام شد.
- Synthetic self-check برای یکتایی Row، Controls، دامنهٔ کلاس و هم‌ترازی بردارها
  PASS؛ شمارش نهایی، عدم معیار ساختگی و normalized provenance نیز PASS.
- تست متمرکز `test_expanded_inventory.py`: یک تست با چند Assertion در5.809s،
  PASS؛ یکتایی1344 ردیف Synthetic، Controlهای اضافه و Dedup واقعی Alias تأیید شد.
- ایراد Tuple/List در JSON Readback ابزار تازه رفع شد؛ Source و قرارداد علمی
  تغییر نکرد. Parent Inventory حفظ شد. فرزند نهایی Controls اضافه و Metadata
  normalize‌شده دارد؛ شواهد بازخوانی قبلی دوباره مصرف شد، Training تکرار نشد.
- Full Suite و CI جدید اجرا نشدند؛ کدهای قدیمی تغییر نکردند و این Slice فقط
  آماده‌سازی است. هیچ ادعای CI یا Training جدید نداریم.

گام اجرایی بعدی نیازمند تأیید مستقل برای بستهٔ آماده‌سازی، Adapter Admission توسعه‌یافته
و1720 Fit جدید است. مجوز Full GCN v1 به این دامنه تعمیم داده نشده است. GT-only
آینده فقط پس از Freeze Fitهای جدید و با مجوز جدا انجام خواهد شد. فعلاً توقف.
