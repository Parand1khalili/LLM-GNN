# دفتر شواهد پایان‌نامه — Cora140 / B1 / Narrative-v0 / SARA-3 / Routing

## Revision: receipt-derived correction slice — 2026-11-07

An independently executed GT-free extraction froze 74 router observations /57
unique nodes before a separate GT-only process reproduced Narrative-to-Blind
five-outcome counts R0=7/6/12/5/7 and R1=3/2/14/6/12 (fix/harm/both-correct/
both-incorrect/no-class). Feature SHA e4b2724a7b05abb4eeede9ed53e93592cdb94911a673ba9b245aa17e6d86e7fe;
private outcome SHA1501dac6d417511503cfb8a9a03bf3310beba6b6927ab956d9b1b131c668109c.
The conservative eligibility is V1-equivalent: zero shadow changes, no new V2,
no admissions and no GCN training. This is EXPLORATORY_NOT_INDEPENDENT, not a
confirmation on new data. Details/limitations: docs/CORRECTION_FEATURES_V1.md.
Historical figures below are preserved. Code reference before slice:8f88007.

**وضعیت:** ۲۰۲۶-۱۱-۰۷؛ داده‌های مشاهداتی واقعیِ گزارش‌شده از Windows مالک، به‌همراه ارزیابی GT-only آفلاین. این سند عمومی فقط آمار تجمیعی، محدودیت‌ها و مسیرهای بازتولید را نگه می‌دارد؛ **هیچ GT نودبه‌نود، متن خصوصی مقاله، Receipt مدل، کلید API یا گزارش owner-private را شامل نمی‌شود.**

## ۱. تعریف داده، منشأ و مرزهای ادعا

- گراف Cora شامل **۲۷۰۸ گره و ۷ کلاس** است. آزمایش SARA-3 روی **۱۴۰ نود منجمد** انجام شده است. هر Router دقیقاً **۳۷ نود** از همین ۱۴۰ نود را انتخاب می‌کند؛ ۱۰۳ نود دیگر از بازبینی Router موردنظر خارج می‌مانند.
- Baselineهای منجمد: `B1` و `Narrative-v0`. Ground Truth اصلی فقط **پس از انتخاب، پایان پاسخ Agent و Freeze** در ارزیابی خصوصی استفاده شده است. Graph اصلی owner-local: `.local_artifacts/gt_reference/cora_random_sbert.pt`، SHA-256 برابر `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`.
- ارزیابی Router شامل تشخیص «حداقل یکی از B1/Narrative اشتباه است» و تشخیص «هر دو روی یک کلاس اشتباه توافق دارند» است؛ این‌ها **دقت طبقه‌بندی نهایی یا GCN نیستند**.
- R1-v1 موجود یک **بازسازی candidate** از Router مفهومی تاریخی R1 است؛ هم‌ارزی الگوریتمی با R1 تاریخی هنوز تأیید نشده است. R0 اجرای اصلی واقعی را داشته؛ R1-v1 بعداً به‌صورت Live جداگانه اجرا شد.
- پیکربندی Gateway مدل مورددرخواست `gpt-6-luna` از طریق GapGPT را ثبت کرده است؛ هویت واقعی مدل برگشتی، تعرفه و شرایط نگهداری دادهٔ سرویس‌دهنده مستقلاً تأیید نشده است. Blind و Comparison دو فاز مرتبط یک مدل‌اند و توافقشان استقلال آماری دو داور را اثبات نمی‌کند.

## ۲. آمار پایهٔ ثابت در ۱۴۰ نود

| شاخص | تعداد |
|---|---:|
| B1 صحیح | 96/140 (68.5714%) |
| Narrative-v0 صحیح | 101/140 (72.1429%) |
| B1 اشتباه | 44 |
| Narrative-v0 اشتباه | 39 |
| حداقل یکی اشتباه (`either_wrong`) | 45 |
| هر دو اشتباه (`both_wrong`) | 38 |
| هر دو بر یک کلاس غلط توافق دارند (`agreed_wrong`) | 36 |
| اختلاف بین دو Baseline (`disagreement`) | 9 |

نکته: **۳۶ توافق غلط** زیرمجموعه‌ای از ۳۸ موردی است که هر دو Baseline غلط‌اند؛ دو حالت دیگر ممکن است دو کلاس غلط متفاوت داشته باشند.

## ۳. کیفیت Routing — ارزیابی Post-hoc / Exploratory

تمام شش سیاست با بودجهٔ یکسان ۳۷/۱۴۰ و GT ثابت مقایسه شده‌اند.

| Router | TP خطای حداقل یک Baseline | FP | FN | TN | Precision | Recall | توافق غلط کشف‌شده (از ۳۶) | هم‌پوشانی با R0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R0 | 22 | 15 | 23 | 80 | 59.4595% | 48.8889% | 13 | 37 |
| Semantic-v0 | 19 | 18 | 26 | 77 | 51.3514% | 42.2222% | 10 | 25 |
| **R1 candidate v1** | **24** | **13** | **21** | **82** | **64.8649%** | **53.3333%** | **17** | 17 |
| R1 Neutral v1 | 21 | 16 | 24 | 79 | 56.7568% | 46.6667% | 12 | 18 |
| R1 candidate v2 | 14 | 23 | 31 | 72 | 37.8378% | 31.1111% | 8 | 15 |
| R2 candidate v1 | 19 | 18 | 26 | 77 | 51.3514% | 42.2222% | 10 | 27 |

تفکیک R0 و R1-v1: R0 از ۹ اختلاف Baseline هر ۹ مورد را انتخاب کرده؛ R1-v1 هفت مورد را. R0 تعداد ۲۱ خطای B1، ۱۶ خطای Narrative، ۱۵ «هر دو غلط» و ۱۳ «توافق غلط» را انتخاب کرد. R1-v1 به‌ترتیب ۲۳، ۲۰، ۱۹ و ۱۷ مورد را انتخاب کرد.

هم‌پوشانی انتخاب‌های R0/R1-v1 **۱۷ نود** است، در نتیجه اتحاد دو مجموعه **۵۷ نود یکتا** دارد؛ از خطاها، **۱۳ مشترک، ۹ فقط R0 و ۱۱ فقط R1-v1** بودند و اتحادشان ۳۳ خطای واقعی در میان ۵۷ انتخاب داشت. این یک تحلیل Post-hoc با بودجهٔ بالاتر است، نه Router ترکیبیِ اجراشده یا آزمایش هم‌بودجه. نتیجهٔ «R1-v1 بهترین Error Detection مشاهده‌شده در همین Cohort است» **توصیفی** است؛ نه تضمین برتری در نمونهٔ جدید.

## ۴. R0 — پاسخ واقعی Agent و نتیجهٔ تصحیح

R0 روی ۳۷ نود واقعی Blind/Comparison اجرا شده است؛ پاسخ‌های معتبر و Abstentionها در Journal منجمد موجودند.

| شاخص روی ۳۷ نود R0 | B1 | Narrative-v0 | Blind | Comparison |
|---|---:|---:|---:|---:|
| پاسخ کلاسی | 37 | 37 | 30 | 27 |
| صحیح | 16 | 21 | 19 | 17 |
| صحیح / پاسخ کلاسی | 43.2432% | 56.7568% | 63.3333% | 62.9630% |

| مقایسهٔ زوجی R0 | اصلاح درست Baseline | تخریب Baseline صحیح | سود خالص |
|---|---:|---:|---:|
| B1 → Blind | 8 | 4 | +4 |
| Narrative → Blind | 7 | 6 | +1 |
| B1 → Comparison | 5 | 2 | +3 |
| Narrative → Comparison | 4 | 4 | 0 |

سناریوی **صرفاً فرضی** نگه‌داشتن Narrative و جایگزینی پاسخ‌های موجود: Narrative `101/140`، R0+Blind `102/140`، R0+Comparison `101/140`. این **Arbitration V1 واقعی یا Accuracy مدل GCN نیست**. نودهای Reviewed پذیرفته‌شده برای آموزش: **صفر**؛ بدون Human L2 و بدون اجرای واقعی GCN.

## ۵. R1-v1 — گزارش نهایی پس از Continuation واقعی

- اجرای اولیه: **۵۱ درخواست**؛ ۵۰ پاسخ `COMPLETED`، یک Comparison با `L1_QUOTE_NOT_FOUND` (HTTP 200، JSON معتبر، `finish_reason=stop`) `REJECTED`، صفر درخواست `UNCERTAIN`؛ ۳۰ فاز Blind و ۲۰ Comparison تکمیل شده بودند.
- Continuation با Approval مستقل: **۱۱ درخواست جدید، هر ۱۱ موفق**؛ ۷ Blind و ۴ Comparison؛ هیچ درخواست اولیه بازفرستاده یا حذف نشد. **جمعاً ۶۲ درخواست** (۶۱ موفق و یک Comparison ردشده). همهٔ **۳۷ فاز Blind** انجام شدند؛ **۱۲ Blind Abstention** داشتند، بنابراین **۲۵ پاسخ کلاسی Blind** وجود دارد. تعداد Comparisonهای موفق/دارای کلاس **۲۴** است و مورد نامعتبر اصلی حفظ شده است.
- در خروجی Windows، ارزیاب جداگانهٔ GT-only وضعیت `R1_CONTINUED_GT_NODE_JOURNEY_VERIFIED_PRIVATE` و `R1_FINAL_GT_EVALUATION_VERIFIED` را گزارش کرد. نتیجهٔ Node-level فقط روی دستگاه مالک است.

| شاخص روی ۳۷ انتخاب R1-v1 | B1 | Narrative-v0 | Blind | Comparison |
|---|---:|---:|---:|---:|
| پاسخ کلاسی | 37 | 37 | 25 | 24 |
| صحیح | 14 | 17 | 17 | 15 |
| صحیح / پاسخ کلاسی | 37.8378% | 45.9459% | 68.0% | 62.5% |
| بدون پاسخ کلاسی | 0 | 0 | 12 | 13 |

| مقایسهٔ زوجی R1-v1 | اصلاح درست Baseline | تخریب Baseline صحیح | سود خالص |
|---|---:|---:|---:|
| B1 → Blind | 4 | 1 | +3 |
| Narrative → Blind | 3 | 2 | +1 |
| B1 → Comparison | 3 | 2 | +1 |
| Narrative → Comparison | 2 | 3 | −1 |

سناریوی فرضی روی کل ۱۴۰: Narrative `101/140`؛ R1-v1+Blind `102/140`؛ R1-v1+Comparison `100/140`. تعداد Admission واقعی از ۳۷ Reviewed برابر **صفر**؛ `total_frozen_training_admissions=78` برچسب‌های **Baseline موجود** هستند و نباید به‌عنوان ۷۸ اصلاح پذیرفته‌شدهٔ Agent تعبیر شوند. هیچ GCN اجرا نشده است.

توزیع Veto نهایی R1: `AUXILIARY_METHOD_WARNING=15`، `BLIND_ABSTENTION=12`، `COUNTER_EVIDENCE_UNRESOLVED=4`، `THIRD_CLASS_DIAGNOSTIC_ONLY=5`، `L1_QUOTE_NOT_FOUND=1`؛ جمع ۳۷.

- Counter-evidence: ۴/۴ Blind و Comparison صحیح‌اند، اما Narrative نیز ۴/۴ صحیح بوده است؛ **سود افزودهٔ صفر**.
- Third-class: ۵ مورد؛ Narrative ۲/۵، Blind ۲/۵، Comparison ۱/۵؛ Blind در این گروه ۱ اصلاح و ۱ تخریب، Comparison یک اصلاح و دو تخریب. توافق Blind و Comparison روی کلاس سوم در ۴ مورد فقط ۱/۴ صحیح بوده است؛ **توافق دو فاز به‌تنهایی مجوز Admission نیست**.
- Other: ۲۸ مورد؛ Blind ۱۱ صحیح از ۱۶ پاسخ کلاسی، Comparison ۱۰ صحیح از ۱۵؛ Narrative ۱۱/۲۸ صحیح.

## ۶. محدودهٔ آماری تحلیل مشترک برای Arbitration

- واحد آماری صحیح برای داده‌های دو Router **(router, node_id, phase)** است. اگر فقط Blind در مقابل Narrative را در نظر بگیریم: R0 برابر **۷ اصلاح مفید، ۶ تخریب** و R1-v1 برابر **۳ اصلاح مفید، ۲ تخریب**؛ جمع ساده **۱۰ اصلاح و ۸ تخریب در سطح «مشاهدهٔ Router»** است، **نه ۱۸ گره مستقل**، چون ۱۷ گره بین دو Router هم‌پوشانی دارند. رویداد مشترک یک node می‌تواند دو پاسخ واقعی متفاوت از دو اجرای جداگانه داشته باشد.
- برای تصویر کامل باید ۱۲ `BOTH_CORRECT` و ۵ `BOTH_INCORRECT` و ۷ بدون پاسخ Blind در R0، و ۱۴ `BOTH_CORRECT` و ۶ `BOTH_INCORRECT` و ۱۲ بدون پاسخ Blind در R1 را نیز نگه داشت. تعریف Outcome برای R1 کامل: Narrative-vs-Blind `CORRECTED=3, DAMAGED=2, BOTH_CORRECT=14, BOTH_INCORRECT=6, NO_CLASS=12`؛ برای R0: `7,6,12,5,7`.
- ویژگی‌های مجاز GT-free: توافق/اختلاف و confidence دو Baseline؛ پاسخ و Abstention هر فاز؛ صحت L1 و وجود Quote منطبق با متن؛ Counter-evidence؛ Auxiliary Method Warning؛ Uncertainty؛ Primary Topic و همخوانی آن میان دو فاز؛ اشتراک Quoteهای واقعی؛ Third-class بودن؛ وضعیت و دلیل Veto. باید قبل از اتصال به Outcome خصوصی استخراج و Freeze شوند.
- موارد ممنوع به‌عنوان Input: `ground_truth`, `y`, `oracle_flags_posthoc`, `*_correct`, `*_wrong`, `narrative_to_blind`, `CORRECTED_BASELINE_ERROR`, `DAMAGED_CORRECT_BASELINE` و هر نتیجهٔ GT-only؛ تاریخچهٔ HTTP/مدل را نیز نباید از روی GT تنظیم کرد.

## ۷. طراحی پژوهش پیشنهادی و محدودیت‌ها برای پایان‌نامه

**فرضیهٔ اکتشافی H1:** بعضی ویژگی‌های قابل‌اندازه‌گیری بدون GT می‌توانند بین اصلاح سودمند و تخریب برچسب در پاسخ‌های موجود همراهی نشان دهند. به‌دلیل تعداد اندک و انتخاب Post-hoc، این همراهی آزمون تأییدی نیست.

**فرضیهٔ اکتشافی H2:** یک سیاست Arbitration کوچک، ثابت و Conservative با عدم‌پذیرش خودکار Third-class/شواهد متعارض می‌تواند خطر Admission غلط را کاهش دهد، ولی ممکن است Recall و Coverage اصلاح را کاهش دهد یا هیچ اصلاحی را قبول نکند. اگر Rule با همین ۱۴۰ GT تنظیم شد، عملکرد همین ۱۴۰ فقط **Development/Exploratory** است.

**فرضیهٔ آینده H3 (هنوز ارزیابی نشده):** Admission GT-free تأییدشده ممکن است Accuracy مدل GCN را نسبت به Baseline تغییر دهد. برای آزمون آن باید Split و Hyperparameterها قبل از رؤیت نتایج قفل شوند؛ آزمایش Control و Treatment با Seed/Graph/Config/ماسک Test یکسان اجرا شود؛ GT فقط پس از Training برای ارزیابی Test استفاده شود؛ و هیچ‌یک از ۱۴۰ GT افشاشده نباید «تأیید مستقل» نامیده شود.

**تهدیدهای اعتبار:** Selection Bias در انتخاب R1/آستانه‌ها روی GT همین ۱۴۰؛ وابستگی مشاهدات دو Router؛ دو فاز یک LLM؛ Selective Accuracy فقط روی پاسخ‌دارها؛ اهمیت Abstention/Quote L1 failure؛ ناپایداری نمونهٔ کوچک؛ هویت/قیمت/حریم خصوصی تأییدنشدهٔ Provider؛ transductive بودن گراف (اجازهٔ feature/edge، نه test labels)؛ احتمال استفادهٔ قبلی از ۲۵۶۸ برچسب Test در تصمیم‌های گذشته که نیازمند Audit است.

**واژه‌گذاری پیشنهادی پایان‌نامه:** «Retrospective exploratory GT-only routing diagnostic»، «real frozen SARA-3 Blind/Comparison responses»، «paired correction-versus-harm descriptive contrast»، «shadow arbitration proposal»، «controlled matched-seed GCN ablation»، «independent held-out evaluation only after contamination audit».

## ۸. پیوندها و مسیرهای بازتولید در Repository

- `PROJECT_STATE.md` — منبع وضعیت پروژه و سابقهٔ رویدادها.
- `docs/CORA140_ALL_ROUTERS_GT_EVALUATION.md` و `src/llmgnn_sara/evaluation/cora_all_routers_gt.py` — شش Router با GT آفلاین.
- `docs/CORA140_NODE_JOURNEY_EVALUATION.md` و `src/llmgnn_sara/evaluation/cora_node_journey.py` — R0 خصوصی.
- `docs/CORA140_R1_V1_CONTINUATION.md` و `src/llmgnn_sara/evaluation/cora_r1_continued_gt.py` — تکمیل R1 و ارزیابی خصوصی.
- `src/llmgnn_sara/sara3/automated_policy.py` — Arbitration V1 فعلی با محافظت‌های GT-free.
- `src/llmgnn_sara/downstream/{plan.py,prospective.py,model.py}` — GCN plan و Guard آموزشی؛ `train_gcn` نیازمند `allow_training=True` و مجوز مستقل است.
- `configs/gapgpt_rich_v2_output4096_proposed.json` — قرارداد درخواست؛ تعرفه و مدل Provider باید هنگام نوشتن پایان‌نامه مجدداً Verify شوند.

### ثبت برای استفادهٔ بعدی

این سند باید همراه با Commit SHA و تاریخ مطالعه مورد استناد قرار گیرد. در این محیط Project، Memory گفتگویی غیرفعال است؛ نسخهٔ Commit‌شدهٔ Markdown راه پایدارتر و قابل‌بازیابی اطلاعات پایان‌نامه است. جزئیات خصوصی فقط روی Windows مالک باقی می‌مانند و در GitHub یا نگارش عمومی پایان‌نامه نباید در قالب Node-ID+GT منتشر شوند.
