# دستورکار اجرایی برای Codex — SARA-3 Correction Diagnostics → Arbitration V2 Shadow → Controlled GCN Ablation

**تاریخ:** ۲۰۲۶-۱۱-۰۷  
**Repository:** `Parand1khalili/LLM-GNN`  
**Branch مجاز برای تغییر:** صرفاً Branch موجود `main`؛ **ساخت Branch یا Pull Request (حتی Draft) ممنوع، مگر با دستور صریح جدید مالک**.  
**اولویت:** یک Vertical Slice کامل و قابل‌آزمون در هر مرحله، بدون مدل یا Router جدید، **بدون هیچ API Call جدید** و بدون تغییر در داده‌های منجمد، R0/R1 live journals یا سیاست فعلی.

## هدف و محدوده

تمام آزمایش‌های Router روی Cohort ثابت Cora140 و هر دو اجرای واقعی Agent (R0 و R1-v1 پس از Continuation) موجودند. اکنون باید بدون مصرف مدل جدید، شواهد **GT-free** موجود در خروجی دو فاز Blind/Comparison را به‌صورت قابل‌بازتولید استخراج کنی؛ سپس آن‌ها را فقط در مرحلهٔ خصوصی Post-hoc با Outcomeهای **اصلاح درست** / **خراب‌کردن برچسب صحیح** مقایسه کنی؛ یک سیاست کوچک و نسخه‌دار **Arbitration V2 در حالت Shadow** تعریف کنی؛ و در صورت احراز شرایط استقلال داده و Approval آموزش، یک **Controlled GCN Ablation** با Control/Treatment همسان اجرا کنی. هیچ ادعای Confirmatory Accuracy روی همان ۱۴۰ GT شناخته‌شده مجاز نیست.

## نتایج مستند موجود — این‌ها را مبنا قرار بده، نه حدس

### Cora140 و Routerها

- Cora کامل: ۲۷۰۸ نود، ۷ کلاس. Cohort بررسی: ۱۴۰ نود ثابت. بودجهٔ هر Router: ۳۷ نود.
- B1 صحیح `96/140`، Narrative-v0 صحیح `101/140`. خطای B1: `44`، Narrative: `39`، `either_wrong=45`، `both_wrong=38`، `agreed_wrong=36`، disagreement دو Baseline: `9`.
- R0: TP/FP/FN/TN برابر `22/15/23/80`، Precision `59.4595%`، Recall `48.8889%`، توافق اشتباه شناسایی‌شده `13/36`، اختلاف Baseline شناسایی‌شده `9/9`.
- R1 candidate v1: `24/13/21/82`، Precision `64.8649%`، Recall `53.3333%`، توافق اشتباه `17/36`، اختلاف Baseline `7/9`، ۱۵ توافقِ دو Baseline با confidence بالا در انتخاب R1.
- انتخاب R0/R1-v1 فقط روی `17` نود هم‌پوشانی دارد؛ اتحادشان `57` نود یکتاست. از ۴۵ خطا، ۱۳ مشترک، ۹ فقط R0 و ۱۱ فقط R1 پیدا شده است. بنابراین خروجی R0/R1 نمونه‌های کاملاً مستقل نیستند.
- سایر Routerها، همگی صرفاً GT-only routing: Semantic `19/37`، R1 Neutral `21/37`، R1 v2 `14/37`، R2 v1 `19/37` نود خطادار را یافتند. **R1-v1 فعلی یک بازسازی candidate است، نه الزاماً همان R1 تاریخی.**

### اجرای واقعی SARA-3 و اصلاح برچسب

| مقدار روی ۳۷ نود | R0 | R1-v1 نهایی |
|---|---:|---:|
| B1 صحیح | 16 | 14 |
| Narrative صحیح | 21 | 17 |
| Blind با پاسخ کلاسی | 30 | 25 |
| Blind صحیح | 19/30 | 17/25 |
| Comparison با پاسخ کلاسی | 27 | 24 |
| Comparison صحیح | 17/27 | 15/24 |
| Blind Abstention | 7 | 12 |
| Narrative→Blind: اصلاح صحیح / تخریب صحیح | **7/6** | **3/2** |
| Narrative→Comparison: اصلاح / تخریب | 4/4 | 2/3 |
| B1→Blind: اصلاح / تخریب | 8/4 | 4/1 |
| B1→Comparison: اصلاح / تخریب | 5/2 | 3/2 |
| Reviewed Agent label admissions | 0 | 0 |

- تعداد صحیح Narrative در کل۱۴۰ `101` است. «جایگزینی صرفاً فرضی پاسخ‌های دارای کلاس»: R0+Blind `102`، R0+Comparison `101`؛ R1+Blind `102`، R1+Comparison `100` از ۱۴۰. این اعداد **نه Admission V1 و نه GCN Accuracy** هستند.
- R1 واقعی: اجرای اولیه ۵۱ درخواست (۵۰ Completed، یک Rejected Comparison با `L1_QUOTE_NOT_FOUND`، صفر Uncertain). Continuation مستقل ۱۱ درخواست جدید موفق انجام داد (۷ Blind و۴ Comparison)، مجموع **۶۲ درخواست**؛ ۳۷ Blind تکمیل، ۱۲ Abstain، ۲۵ پاسخ کلاسی و ۲۴ Comparison معتبر؛ مورد ردشده قدیمی حفظ شده است. هرگز آن را retry یا با برچسب فرضی پر نکن.
- دلیل تصمیم نهایی R1: `AUXILIARY_METHOD_WARNING=15`, `BLIND_ABSTENTION=12`, `COUNTER_EVIDENCE_UNRESOLVED=4`, `THIRD_CLASS_DIAGNOSTIC_ONLY=5`, `L1_QUOTE_NOT_FOUND=1`. چهار مورد Counter-evidence همگی در Narrative نیز درست بودند. روی پنج Third-class، Blind `2/5` و Comparison `1/5` درست بودند؛ از چهار توافق فازی روی Third-class فقط `1/4` صحیح بود. توافق دو فاز یک LLM **به‌خودی خود استقلال یا تأیید معنایی نیست**.
- `total_frozen_training_admissions=78` در ارزیابی R1، **پذیرش‌های قبلی Baseline** است، نه ۷۸ اصلاح پذیرفته‌شدهٔ Agent. هیچ آموزش واقعی GCN، Human L2 و بهبود نهایی مدل گزارش نشده است.

**مرجع پایدار:** `docs/THESIS_EVIDENCE_LEDGER_CORA140_2026-11-07_FA.md` و `PROJECT_STATE.md` و اسناد GT و Continuation. فایل‌های `.local_artifacts/` فقط در Windows مالک وجود دارند؛ نبود آن‌ها در GitHub و CI عادی است.

## قوانین غیرقابل‌مذاکره

۱. **بدون API / مدل جدید / Router جدید / Rerun R0 یا R1**. ورودی فقط پاسخ‌ها و Receiptهای واقعاً Freeze‌شده‌اند. هیچ Provider Call حتی برای «کیفیت Evidence» مجاز نیست.
۲. **Ground Truth هرگز به Selection، Prompt، Feature Extraction، Rule Engine، Admission یا Training وارد نشود.** دو Process / Module با Allowlist مستقل بساز: **(الف) GT-free Extraction & Shadow Policy**، **(ب) فقط Post-hoc Evaluator که خروجی منجمد الف را به GT خصوصی Join می‌کند**. جلوی Import مستقیم محتوای GT-only به مسیر الف را بگیر.
۳. حفظ immutability و integrity: Context SHA، Freeze SHA، original Graph SHA، original/overlay receipt identities، cohort و class order را پیش از ارزیابی بررسی کن؛ `FAIL_CLOSED` با فایل غایب، SHA اشتباه، نود اضافه/تکراری، علت نامعلوم یا provenance نامعتبر.
۴. **هیچ GT نودبه‌نود، خروجی raw LLM، Secret، Prompt دارای دادهٔ خصوصی، Journal یا owner-private metrics به GitHub / لاگ عمومی / issue / PR / chat ارسال نشود.** گزارش عمومی فقط aggregate بدون ID یا pairing حساس؛ خروجی Node-level فقط content-addressed در `.local_artifacts/` و با Hash Readback.
۵. V1 و Freeze فعلی را تغییر نده. `automated_policy.py` V1 را به‌عنوان Baseline حفظ کن؛ Proposal هرگز معادل «Label Approved for Training» نباشد. Real GCN Training دارای Gate مجوز جداگانه است.
۶. همهٔ تحلیل‌های مبتنی بر این ۱۴۰ GT **Exploratory/Post-hoc** هستند. اگر از همین GT برای انتخاب Predicate یا Threshold استفاده شد، حق نداری امتیاز روی همین ۱۴۰ را Independent Validation بخوانی؛ هیچ Hyperparameter/Seed/Policy را بر اساس Test جدید Tune نکن.
۷. Branch/PR جدید نساز. فقط روی `main` موجود با Git fast-forward و بدون Force-push، Reset، Rewrite یا تغییر unrelated کار کن؛ پیش از هر Commit وضعیت HEAD را دوباره چک کن.

## فاز A — GT-free Feature Extraction از دو اجرای واقعی

**۱. بازرسی بدون تغییر:** کد و تست‌های `src/llmgnn_sara/evaluation/cora_node_journey.py`, `cora_r1_continued_gt.py`, `cora_r1_real_gt.py`, `sara3/automated_policy.py`, `sara3/gateway_continuation.py`, `sara3/gateway_r1_continuation.py`, `sara3/rich_evidence.py`, `sara3/audit.py`, `downstream/{plan,prospective,model}.py`. Source-of-truth هر پاسخ، **Receipt واقعی L1-validated** است، نه فیلد پیش‌بینی کلاسیِ قابل‌ویرایش در Report تجمیعی. R1 را از original+overlay بخوان؛ حالت Rejected باید Rejected بماند. هر ردیف Node ID داشته باشد اما خروجی private باشد.

**۲. طراحی سادهٔ Schema نسخه‌دار برای ۷۴ مشاهدهٔ `(router,node_id)`** (۳۷ R0 +۳۷ R1، ۱۷ ID هم‌پوشان/۵۷ unique). ویژگی‌ها کاملاً GT-free و تعیین‌پذیر باشند؛ فهرست زیر را ابتدا پیش‌ثبت کن و بعد Outcomeها را Join کن:

- Baseline agreement/disagreement؛ کلاس‌ها و Confidence دو روش و min/max/gap؛ مطابق قرارداد منجمد، بدون GT.
- Blind/Comparison: اعتبار و نتیجهٔ L1، وجود پاسخ کلاسی یا Abstention، توافق دو فاز، تعلق Label پیشنهادی به یکی از کلاس‌های Baseline یا Third-class بودن، class-change relative to Narrative (بدون تشخیص درست/غلط).
- Evidence: تعداد نقل‌قول‌های Supporting/Counter با Source واقعی `target.text` و صحت رشتهٔ دقیق، طول نقل‌قول، تعداد Quoteهای مشترک دو فاز، وجود/تعداد Counter-evidence، وجود Auxiliary Method Warning، وجود Uncertainty Reason، همخوانی Primary Topic دو فاز (normalization ثابت و فقط برای مقایسه). اگر مقدار unavailable است `None` و دلیل Missingness ثبت شود؛ نباید بسازی یا حدس بزنی.
- V1 first-veto reason و وضعیت کامل‌بودن هر فاز به‌عنوان مشخصهٔ تشخیصی، **نه Ground Truth Label**؛ مراقب Circularity باش. Raw text و Evidence را در Aggregate یا GitHub منتشر نکن.

**۳. تست عدم نشت:** Schema allowlist دقیق، رد کلیدهای `gt`, `label_truth`, `ground_truth`, `oracle`, `correct`, `wrong`, `y`, `narrative_to_blind`, `DAMAGED_...`, `CORRECTED_...` و هر فیلد derived-from-GT؛ شبکه در تست‌ها مسدود شود. هیچ API Key در Test Fixture نگذار. Feature Extraction باید بدون وجود فایل GT قابل‌اجرا باشد، Output ثابت و Hash-pinned تولید کند، و هشدار/source missingness را درست ثبت کند.

**خروجی A:** Feature table خصوصی با `feature_schema_version`, `policy-independent`, `source_run_sha256`, `selected_count=37 each`, `n_observations=74`, `unique_nodes=57`, `feature_digest`, plus aggregate feature distributions (بدون GT) و تست‌ها. اگر این ۵۷/۷۴ با دادهٔ واقعی ناسازگار شد، Fail closed و اختلاف را گزارش کن؛ عددها را دست‌کاری نکن.

## فاز B — Post-hoc Outcome Analysis، فقط در Process خصوصی

۱. از گزارش خصوصی R0 `.local_artifacts/sara3_gt_node_journey_v1/` و R1 تکمیل‌شده `.local_artifacts/sara3_r1_v1_continued_gt_v1/` استفاده کن، پس از Verify Graph SHA و Source SHA. منبع صحیح/غلط فقط اصلی‌ترین GT Cora است. با `(router,node_id)` Join قطعی و one-to-one انجام بده؛ هیچ GT به Feature Extractor یا Rule Engine منتقل نشود.

۲. در قیاس **Narrative→Blind** پنج دستهٔ کامل را برای هر Router نگه دار: `CORRECTED_BASELINE_ERROR`, `DAMAGED_CORRECT_BASELINE`, `BOTH_CORRECT`, `BOTH_INCORRECT`, `NO_CLASS_PREDICTION`. دسته‌های مشابه Comparison و نسبت به B1 هم گزارش شوند. نتیجهٔ ۷/۶ در R0 و ۳/۲ در R1 نقطهٔ تمرکز است، اما فقط ۱۸ رویداد «Fix/Harm» از **داده‌های وابسته** داریم؛ بقیه را حذف نکن.

۳. برای هر ویژگی GT-free، جدول توزیع کوچک (counts, denominators, missingness, numerator، ریسک مشروط با confidence interval مناسب *فقط توصیفی*) بین `fix` و `harm` تولید کن. به‌دلیل تعداد اندک، از ML classifier، grid search، آستانه‌یابی دقیق روی GT، p-value نتیجه‌محور و ادعای significant خودداری کن. تضاد R0/R1، وضعیت Agent Abstention و مورد L1 ردشده را جدا نمایش بده. اگر Bootstrap استفاده شد، **Cluster بر اساس node_id** و محدودیت حجم نمونه ذکر شود؛ گزارش درصدهای بدون denominator ممنوع.

۴. جدول Failure Mode (Counter Evidence/Topic Drift/Auxiliary/Third-class/Missing Quote/Missing Agent phase/Abstention) و ۱۰ نمونهٔ Fix و ۸ نمونهٔ Harm در سطح **رویدادهای انتخاب** با Featureهای GT-free فراهم کن، اما Node IDs، GT و متن‌های خصوصی فقط در گزارش Owner-local؛ هیچ نمونهٔ واقعی در GitHub قرار نگیرد. نشان بده هر ویژگی چرا قابل مشاهده در زمان تصمیم‌گیری است.

**خروجی B:** گزارش Markdown عمومیِ بی‌هویت حاوی Counts/Limitations و JSON owner-private کامل با Hash. گزارش نتیجه را صریحاً `EXPLORATORY_NOT_INDEPENDENT` بنام.

## فاز C — Arbitration V2 Shadow؛ نسخه‌دار، محافظه‌کار، بدون Admission واقعی

۱. ابتدا V1 فعلی `sara.arbitration.automated_concordance.v1` را بررسی کن. اگر قانون پیشنهادشده عین V1 است، به‌جای خلق نسخهٔ بی‌فایده، Equivalence را مستند کن؛ V2 فقط وقتی نسخهٔ مستقلی است که تفاوت رفتاریِ صریح و تست‌شده داشته باشد. **قانون از ابتدا و پیش از اندازه‌گیری عملکرد آن Freeze/Version شود**؛ جدول B فقط برای تعریف فرضیهٔ اکتشافی است، نه تأیید آن.

۲. نمونهٔ پیش‌ثبتِ Rule ایمن و ساده (قابل اصلاح صرفاً با دلیل روش‌شناختی، نه بهینه‌سازی همان GT): فقط اگر هر دو پاسخ موجود و L1 PASS، هر دو غیرAbstain، کلاس یکسان و معتبر، Quoteهای exact `target.text` با حداقل یک Supporting Quote مشترک، Primary Topic یکسان و غیرخالی، بدون Counter-evidence، Warning، Uncertainty و Third-class، یک **Shadow Proposal** برای جایگزینی Narrative بساز؛ اگر کلاس پیشنهادی همان Narrative است `KEEP_BASELINE` (هیچ اصلاحی رخ نداده)؛ بقیه `ABSTAIN` یا `REJECT_L1`. **Third-class حتی با توافق هر دو فاز به‌طور خودکار پذیرفته نشود** و به `L2_REQUIRED` منتقل شود. این محدودیت می‌تواند agreed-wrong را از Admission خودکار محروم کند؛ Trade-off آن را روشن کن.

۳. خروجی Pure Function با نسخهٔ ثابت مانند `sara.arbitration.shadow_conservative.v2`, `rule_digest`, `source_feature_digest`, `decision`, `reason`, `candidate_class_index`, `would_change_narrative`, `l2_status=NOT_ASSESSED`, `training_eligible=False`. برچسب GT، Outcome یا Score در ورودی Rule **مطلقاً ممنوع**؛ نباید Training Labels واقعی را تغییر دهد. اگر صفر Proposal قابل‌قبول شد، نتیجه را صفر ثبت کن؛ Rule را برای بالا بردن Coverage ضعیف نکن.

۴. بدون مدخل‌های قبلیِ Approved، Rule فقط **Shadow Retrospective Replay** شود؛ نرخ Proposal، Abstention، Unavailable، estimated Fix/Harm روی همین ۱۴۰ فقط Post-hoc، با ۳۷ denominator هر Router و تفکیک Phase. تست positive/negative برای fake GT fields، third-class، contradictory quotes، forged L1، missing phase، old rejected Comparison، overlap consistency، determinism و no mutation ضروری است.

**خروجی C:** Rule specification و code/test؛ Version freeze و digest؛ مقایسهٔ Shadow V2 با V1 بدون ادعای Independent Gain؛ بدون Admission و آموزش.

## فاز D — Controlled GCN Ablation فقط پس از Gate استقلال و Approval

۱. از کد موجود `downstream/plan.py`, `downstream/prospective.py`, `downstream/model.py` استفاده کن. GCN تاریخی: ۲۷۰۸ نود، ۷ کلاس، `epochs=30`, `hidden=64`, `layers=2`, `dropout=.5`, `lr=.01`, `weight_decay=.0005`, `seeds=0..9`، بدون Early Stopping، Last-Epoch Checkpoint؛ حفظ CE/WCE و Graph normalization / masks مطابق قرارداد موجود. `train_gcn(..., allow_training=False)` به‌صورت پیش‌فرض Block است؛ **این Gate را حذف یا دور نزن**.

۲. **Audit عدم آلودگی Test:** چون GT همهٔ ۱۴۰ در توسعهٔ Router/Rule دیده شده، آن ۱۴۰ **Hold-out مستقل نیست**. اگر Mask مکملِ ۲۵۶۸ نودی گراف از قبل در تصمیم‌ها/Hyperparameterها دیده نشده و واقعاً دست‌نخورده است، می‌تواند فقط با شواهد Contamination Audit نقش Test را بگیرد؛ در غیر این صورت آزمایش GCN فقط `EXPLORATORY` است و برای ادعای Confirmatory باید Test جدید/مستقل معرفی شود. در گراف transductive خواندن feature/edge نودهای Test ممکن است مجاز باشد؛ **test labels و label-derived features نباید به Train/Selection/Admission برسند**.

۳. Planها را GT-free و با ماسک Test یکسان و feature/edge گراف یکسان بساز:
   - **Control:** همان Baseline pseudo-label admission منجمد (مثلاً ۷۸ مورد گزارش‌شده در اجرای R1، فقط اگر Digest و Cohort و قواعد پذیرش واقعاً تأیید شدند).
   - **Treatment:** دقیقاً همان Control + فقط Shadow Proposalهای Eligibility-checked توسط Rule منجمد با مجوز آزمایشی Admission جدید و مستقل؛ اگر به baseline خلاف کلاس دیگری برخورد کرد، Fail Closed. تعداد پذیرفته‌شده، Class Histogram و Noise Risk را بدون GT در زمان plan گزارش کن.
   - اختیاری، فقط اگر بدون Scope Creep: **No-op sanity control** برای اثبات یکسان‌بودن دو Plan بدون Proposal. اگر صفر Proposal، دو Plan باید یکسان باشند و هیچ اثر جعلی گزارش نشود.

۴. **توجه:** `controlled_gcn_plan` فعلی `provider_calls==0` را enforce می‌کند و برای Offline Synthetic طراحی شده؛ برای Real Live Report آن را تضعیف نکن. اگر لازم است Adapter جداگانهٔ Opt-in بساز که Receiptهای L1 را مستقیم Validate کند، Versioned Consent/Source Pins داشته باشد و همچنان GT-free بماند. بدون Approval آموزش، فقط Plan و synthetic smoke test تولید کن؛ هیچ Real GCN Train را به‌زور فعال نکن.

۵. اگر Data/Graph/Approval/Independent Split معتبر بود، ده Seed ثابت `0..9` را به‌صورت Paired اجرا کن؛ Report `per-seed accuracy`, اختلاف `Treatment - Control`، Mean/SD و paired CI (با احتیاط اندازه نمونه)، `macro-F1`/per-class support در صورت امکان، count of admitted correction labels، coverage، class balance، failure و Device، deterministic flags. در هیچ صورت از Test برای انتخاب V2 Threshold/Seed/Epoch/Hyperparameter استفاده نکن. اگر Split واقعاً مستقل نیست، خروجی را `EXPLORATORY_GCN_ABLATION_NO_INDEPENDENT_CLAIM` نام‌گذاری کن.

**خروجی D:** Config و Plans immutable با hash، test leakage audit، benchmark matched-seed، Result status واقعی `RUN` یا `NOT_RUN_BLOCKED`، Reproduction commands و واضح‌بودن اینکه accuracy واقعاً اندازه‌گیری شده یا نه.

## فاز E — تحویل، تست و ردپای پژوهشی پایان‌نامه

- یک سند مختصر روش‌شناختی شامل سؤال‌ها، Hypotheses، تعریف Sample/Unit of Analysis، Ground Truth Privacy Boundary، Flow Diagram، جدول ۶ Router، جدول R0/R1 Live Accuracy، تهدیدهای اعتبار، گزاره‌های قابل‌دفاع برای پایان‌نامه و چیزهای **هنوز آزمایش‌نشده** بساز. شواهد عددی را به `docs/THESIS_EVIDENCE_LEDGER_CORA140_2026-11-07_FA.md` ارجاع بده؛ نتایج جدیدِ تأییدشده را به‌عنوان Revision با تاریخ/Commit/Artifact Digest به‌روزرسانی کن، بدون جایگزینی خاموش ارقام تاریخی.
- تست‌ها: synthetic positive/negative، هیچ Network، Fail Closed برای GT leak و corrupt receipt/hash/context، refusal unauthorized training، Split train/test overlap، R0/R1 selection mismatch، no original journal mutation؛ سپس `unittest`, relevant lint/typecheck/build اگر موجود و GitHub Actions را اجرا و گزارش کن. شکست‌ها را اصلاح کن، نه اینکه تست ضعیف شود.
- یک End-to-end CLI Owner-local با ورودی rootها و بدون log خصوصی فراهم کن؛ در CI که private files نیستند فقط synthetic tests اجرا می‌شوند و integration واقعی **Skipped/Not Run** صریح اعلام شود.
- تحویل هر Slice شامل فایل‌های تغییرکرده، Traceability به معیارهای Acceptance، Commit SHA روی **main موجود**، تست‌های واقعاً اجراشده، دستور Windows کوتاه، Known Risks و `next gate` باشد. هیچ Branch یا PR نساز؛ Force-push، Reset، Merge PR، یا بازنویسی تاریخچه ممنوع است.

## Acceptance Criteria نهایی

1. دو Run واقعی R0 و R1 از روی Source Pins با **۷۴ مشاهدهٔ Router و ۵۷ نود یکتا** به‌صورت GT-free استخراج شوند؛ ویژگی‌های بدون GT قبل از Join به Outcome جداگانه ذخیره و Hash شوند.
2. Counts تاریخی R0 `7 fix /6 harm` و R1 `3 fix /2 harm` (Narrative→Blind) و کامل بودن پنج Outcome به‌درستی بازتولید شوند، بدون اصلاح یا بارگذاری GT در مرحلهٔ استخراج و تصمیم‌گیری.
3. Rule V2 Shadow deterministic, versioned, no network, no GT, no actual training admission؛ Third-class/Invalid Quote/Abstention محافظت‌شده و صفر Proposal نتیجهٔ معتبر باشد.
4. Plan های Control/Treatment از Graph/Seeds/Masks یکسان و بدون Leakage مشتق شوند. واقعی بودن Independent Test با Audit ثابت شود یا هر گزارش به‌صورت Exploratory مشخص شود.
5. Real GCN Training فقط با Approval جداگانه، و Results/Logs واقعی؛ **هیچ عدد GCN جعلی یا پیش‌فرض** مجاز نیست.
6. Privacy و Owner-private GT، Receipt، API Key و Journal حفظ شوند؛ Repo عمومی فقط aggregate، کد، fake fixtures و مستندات را ببیند.
7. `PROJECT_STATE.md` و Thesis Ledger با آخرین یافته‌های تأییدشده و SHAها به‌روز شوند؛ همهٔ تغییرات روی `main` و هیچ Branch/PR جدیدی ایجاد نشود.

**اصل علمی:** «بهبود Error Detection در R1-v1، بهبود Error Correction یا GCN را تضمین نمی‌کند.» این آزمایش باید دقیقاً فاصلهٔ Routing → Evidence → Arbitration → Admission → GCN را روشن کند، بدون آن‌که GT پسینی به خود تصمیم‌ها نشت کند.
