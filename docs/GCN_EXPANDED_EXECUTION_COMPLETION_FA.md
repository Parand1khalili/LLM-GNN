# تکمیل اجرای GCN Expanded — 2026-11-08

## محدوده و مجوز

این اجرا فقط بستهٔ Frozen زیر را پوشش می‌دهد:
`789a6aea4715c1e7537ede75d82f5e552859c392a0e27acd8cbbbc03b568da83`.
مالک Admission آزمایشی مستقل و حداکثر 1720 Fit جدید را صریحاً تأیید کرد.
رسید Admission خصوصی:
`07660bd2e6236fc9c6a45cc565c6352437fed48243cd287a0bbd493d96ba6b78`.
Admission قبلی بستهٔ `c78ff16d…` تغییر نکرده است.

تمام نتایج `LIMITED_PROVENANCE_EXPLORATORY` و
`EXPLORATORY_NOT_INDEPENDENT` هستند. Test تاریخی 2568 نودی مستقل نیست؛
منشأ اجرای اولیهٔ Encoder به‌طور کامل اثبات نشده است. هیچ Router، Policy،
Label، Confidence، Prompt یا Threshold جدیدی تولید یا تنظیم نشد.

## هویت آزمایش و جلوگیری از تکرار

17 نام Arm، 9 بردار متمایز class/confidence/abstention و 5232 ردیف پیکربندی
وجود دارند. 4044 ردیف داده‌معتبر به 359 Spec مؤثر یکتا نگاشت می‌شوند؛
Seedهای هر Spec برابر 0..9 هستند. هویت Fit شامل Graph، Test-set hash،
Train IDs، Classes، Weights، Config و Runtime است. منشأ Confidence در Ledger
مجزا حفظ می‌شود؛ یکسانی نام یا Accuracy مبنای Reuse نیست.

187 Spec / 1870 Fit از Full GCN v1 قابل Reuse هستند؛ فقط 172 Spec / 1720 Fit
جدید در Admission حاضر قرار دارند. Automated V1 + R1-v1 در اولویت اجرا شد.
GCN، 30 Epoch، CPU، یک Thread و شرایط تاریخی بدون تغییر استفاده شدند.
Intent انحصاری پیش از آموزش نوشته می‌شود. Fit کامل Readback می‌شود؛ Intent
ناقص یا ناسازگار خودکار تکرار، حذف یا بازنویسی نمی‌شود.

## محدودهٔ مسدود و معنای Coverage Gate

- 72 ردیف به‌دلیل Confidence مفقود و 1116 ردیف به‌دلیل تعریف‌نشدن Common
  post-PS mask مسدودند. Extension رسمی فقط در سلول‌های پشتیبانی‌شده اجرا می‌شود.
- 28 ترکیب Router/Policy برای چهار Router فاقد مجموعهٔ پاسخ اصیل و متصل
  به Context همان Router هستند. سه نسخهٔ تاریخی/ناقص دیگر نیز خروجی کامل
  و سازگار برای این مطالعه ندارند.
- 23 نود یکتا پاسخ سازگار ندارند؛ برای 43 نود موجود دیگر، Reuse بین Routerها
  بدون اثبات هویت کامل درخواست مجاز فرض نشده است. شمار API جدید از این
  اطلاعات به‌تنهایی دقیقاً قابل استنتاج نیست؛ هیچ API جدیدی اجرا نشده است.

Gate میان Fit واقعی و قید پیکربندی فاقد Fingerprint معتبر تمایز می‌گذارد.
Ledger دارای `FIT`، `CONFIG_CONSTRAINT`، `MISSING_AGENT_ARM` و `MISSING_VERSION`
است؛ شمار این گروه‌ها نباید با شمار Seed Fit اشتباه شود. حتی پس از تکمیل
همهٔ Fitهای واجد شرایط، وضعیت کل مطالعه به‌دلیل این موانع `PARTIAL_BLOCKED`
و Exit Code آن 1 باقی می‌ماند. `eligible_fits_complete` وضعیت محدودهٔ قابل
اجرا را جدا نشان می‌دهد. ادعای ALL EXPERIMENTS COMPLETED مجاز نیست.

## تفسیر Automated V1 + R1

78 برچسب پذیرفته‌شده و Selective Accuracy برابر 67/78 = 85.90% مربوط به
Raw pseudo-labelهای Sensitivity است؛ این عدد GCN Test Accuracy نیست.
Primary دارای 74 برچسب پیش از PS است. Confidence همان منبع Frozen است.

Control پوشش‌برابر V1+R1 دقیقاً همان IDs، Classes و Confidence را دارد؛
بنابراین Delta آن باید صفر باشد. در Pairwise CE نیز یکسانی برچسب‌ها روی
Mask مشترک، اثر اصلاح کلاسی Agent را نشان نمی‌دهد. نتیجهٔ بهتر Natural
احتمالی را نمی‌توان به‌تنهایی به تصحیح معنایی Agent نسبت داد.

## بازتولید و حریم خصوصی

از Checkout خصوصی مالک، با همان Runtime و داده‌های اصیل:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_experiment_coverage.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.downstream.expanded_execute gate
# فقط پس از احراز تمام Fitهای واجد شرایط و مجوز GT-only:
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.expanded_completion --allow-gt-evaluation
```

فرمان `run` همان ماژول اجرای آموزش، فقط Completeهای معتبر را Reuse می‌کند
و روی Intent نامطمئن متوقف می‌شود؛ راهکار Reset یا Retry خودکار وجود ندارد.
Graph/Features با Reader ایمن و بدون خواندن y به Trainer می‌رسند. Evaluator
در Process مستقل فقط پس از Readback تمام Fitها GT را باز می‌کند. هیچ GT،
Prediction نودبه‌نود یا Checkpoint در گزارش عمومی یا Git قرار نمی‌گیرد.

Artifactهای جدید فقط در `.local_artifacts/expanded_gcn_execution_v1/` هستند.
گزارش‌های Aggregate جاری در `reports/gcn_missing_experiments_results.{csv,json}`
و Ledger در `reports/gcn_experiment_coverage_ledger.csv` قرار می‌گیرند.
Artifactهای تاریخی حفظ می‌شوند؛ این گزارش به‌معنای Backup راه‌دور نیست.

## نتیجهٔ اجرای واقعی و ممیزی

- 1720 Fit جدید واقعاً اجرا شد؛ Process آموزش با Exit Code صفر پایان یافت.
  Smoke Test واقعی نخست Loss را از 1.3281116486 به 0.0620256811 رساند؛
  این مشاهده فقط بررسی عددی همان Fit است، نه معیار انتخاب Model.
- ممیزی پایانی: `VERIFIED_EXISTING=1870`، `EXECUTED_VERIFIED=1720`،
  `BLOCKED=0` و `INVALID=0` برای 3590 Seed Fit تعریف‌شده.
  در سطح Spec: 187 Reuse و 172 اجرای جدید؛ هیچ Spec واجد شرایط Pending نیست.
- هر Fit دارای 30 Loss محدود و نامنفی، Checkpoint و Logits/Predictions
  Hash-verified است. Predictions با Argmax برابرند و Initial Parameter Hash
  در تمام Fitهای هر Seed یکسان است. Artifact فیزیکی غیرمنتظره پیدا نشد.
- رسید Gate:
  `c742b010473c8d6f99205530cff108dedb440d74e7f5f402dabc7aaebc8f2a8e`.
  Ledger خصوصی:
  `6b49e708f4203de9456cb4d62a2b2f1cc531f61bb597d3e76628b69618d7d69c`.
- وضعیت کلی `PARTIAL_BLOCKED` با تنها علت `BLOCKED_CONFIG_ROWS:1219` است:
  1188 قید پیکربندی + 28 Arm فاقد پاسخ + 3 نسخهٔ ناقص.
  Exit Code غیرصفر Gate دقیقاً برای جلوگیری از Completeنمایی این شکاف‌هاست.

## کنترل‌های نرم‌افزاری

چهار تست Coverage Gate اجرا و PASS شدند: Missing/False Complete، Duplicate،
Pending/Invalid/Unexpected، تغییر Hash، Admission نامنطبق و Intent نامطمئن.
Syntax سه فایل جدید PASS شد. Regression گستردهٔ نخست 487 تست داشت و یک
شکست واقعی پیدا کرد: استفادهٔ Runner از `__import__` با قانون ایمنی Runtime
مغایر بود. آن فراخوانی با import مستقیم همان تابع جایگزین شد؛ شش تست CLI
سپس PASS شدند. هیچ قرارداد Frozen یا محاسبهٔ عددی تغییر نکرد.

Regression گسترده پس از اصلاح دوباره اجرا شد: **487 تست، صفر Failure،
صفر Error و دو Skip؛ Exit Code صفر**. لاگ نهایی فقط محلی در
`.local_artifacts/expanded_regression_final.log` حفظ شده است.

دو Skip مربوط به مجوز POSIX روی Windows و نبود اجازهٔ ایجاد Symlink هستند.
شش ماژول خصوصی پایلوت مطابق محدودهٔ CI از این Regression کنار گذاشته شدند؛
این اجرا نباید Full Private Pilot Regression نامیده شود. GitHub Actions در
این تسک اجرا نشده و Push انجام نشده است.

## نتایج واقعی GT-only

Result CAS SHA-256: `d68e87b4cb070556409bb3d8fd4e013b3b87b1420bba1ec47d51682680949a18`.

3590 Seed Fit یکتا ارزیابی شدند؛ 4044 ردیف معتبر و 40440 ردیف Seed با Aliasهای صریح گزارش شده‌اند. 1188 ردیف مسدود بدون معیار باقی ماندند. تمام 1870 معیار Seed تاریخی دقیقاً با خروجی اصلی برابر بودند. 100 مقایسهٔ Seed-paired متمرکز برای V1+R1 ثبت شده است. SD از نوع Population SD است؛ Accuracy درصد و Macro-F1 در بازهٔ 0..1 است.

### Automated V1 + R1 — Natural، پروتکل تاریخی Confidence

| Cohort | Loss | PS | Train | Accuracy ± SD (%) | Macro-F1 | ΔC (pp) | ΔNarrative (pp) |
|---|---|---|---:|---:|---:|---:|---:|
| primary | ce | False | 74 | 73.3684 ± 0.3334 | 0.716999 | +0.9385 | +2.4143 |
| primary | ce | True | 52 | 72.4377 ± 0.3252 | 0.715011 | +0.8139 | +0.5257 |
| primary | wce | False | 74 | 74.3614 ± 0.3198 | 0.729413 | +0.7788 | +1.6900 |
| primary | wce | True | 52 | 73.9058 ± 0.1674 | 0.728599 | +0.9735 | +1.8886 |
| sensitivity | ce | False | 78 | 73.4268 ± 0.3360 | 0.717634 | +0.6503 | +1.6939 |
| sensitivity | ce | True | 55 | 72.5039 ± 0.3246 | 0.715355 | +0.5023 | +0.5296 |
| sensitivity | wce | False | 78 | 74.3769 ± 0.3253 | 0.730101 | +0.5919 | +1.2111 |
| sensitivity | wce | True | 55 | 74.1238 ± 0.1933 | 0.730310 | +0.4984 | +1.8185 |

### تمام 17 نام Arm در یک تنظیم مشترک

Sensitivity140 / Natural / noPS / historical_confidence.v1؛ میانگین ده Seed. BLOCKED یعنی Confidence معتبر کافی در این پروتکل وجود ندارد؛ آن سلول با Extension مخلوط نشده است. تمام Cohortها، Protocolها و Maskها در CSV موجودند.

| Arm | Train | CE Accuracy (%) | CE Macro-F1 | WCE Accuracy (%) | WCE Macro-F1 |
|---|---:|---:|---:|---:|---:|
| A_B1 | 140 | 69.8442 | 0.689759 | 70.5958 | 0.695964 |
| B_NARRATIVE | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |
| CONSENSUS_r0 | 140 | 71.5615 | 0.702047 | BLOCKED | BLOCKED |
| CONSENSUS_r1_v1 | 140 | 71.2422 | 0.695147 | BLOCKED | BLOCKED |
| C_BASELINE_FUSION | 93 | 72.7765 | 0.718796 | 73.7850 | 0.729913 |
| D_P1_r0 | 118 | 69.5600 | 0.681988 | BLOCKED | BLOCKED |
| D_P1_r1_v1 | 108 | 70.9073 | 0.692582 | BLOCKED | BLOCKED |
| E_P2_r0 | 120 | 69.4120 | 0.680843 | BLOCKED | BLOCKED |
| E_P2_r1_v1 | 108 | 70.9073 | 0.692582 | BLOCKED | BLOCKED |
| V1_r0 | 93 | 72.7765 | 0.718796 | 73.7850 | 0.729913 |
| V1_r1_v1 | 78 | 73.4268 | 0.717634 | 74.3769 | 0.730101 |
| V2_DIRECT_r0 | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |
| V2_DIRECT_r1_v1 | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |
| V2_r0 | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |
| V2_r1_v1 | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |
| V3_r0 | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |
| V3_r1_v1 | 140 | 71.7329 | 0.702673 | 73.1659 | 0.722161 |

### بهترین مقدار مشاهده‌شده و تفسیر کنترل‌ها

- بهترین Natural Accuracy: V1+R1 / Sensitivity / WCE / noPS، 74.376947% ± 0.325336، Macro-F1=0.730101، Train=78.
- بهترین Natural Macro-F1: همان Arm / Sensitivity / WCE / PS، 0.730310؛ Accuracy=74.123832% ± 0.193336، Train=55.
- بهترین Coverage-matched no-Agent دقیقاً همین تنظیم‌ها و مقادیر را دارد. تمام Deltaهای V1 نسبت به Control هم‌پوشش، در هر دو معیار و هر Seed صفرند. این دو نتیجه مستقل یا شاهد بهبود ناشی از تغییر کلاس Agent نیستند.
- V1+R1 در هر هشت تنظیم Natural بالا از C و Narrative بالاتر است، اما برچسب‌های آن از Baseline Agreement باقی‌مانده پس از Abstention مسیریابی ساخته شده‌اند. اثر انتخاب/حذف Mask از اثر اصلاح Agent جدا نیست؛ Control هم‌پوشش، افزایش مستقل اصلاح کلاسی را تأیید نمی‌کند.
- انتخاب بهترین سلول از Test تاریخی صرفاً توصیفی و Post-hoc است؛ مجوز تنظیم Rule یا ادعای تعمیم‌پذیری نیست.

### Aliasها و نتایج صفرِ حفظ‌شده

- B_NARRATIVE = V2_r0 = V2_r1_v1 = V2_DIRECT_r0 = V2_DIRECT_r1_v1 = V3_r0 = V3_r1_v1.
- C_BASELINE_FUSION = V1_r0.
- D_P1_r1_v1 = E_P2_r1_v1.
- A_B1، CONSENSUS_r0، CONSENSUS_r1_v1، D_P1_r0، E_P2_r0 و V1_r1_v1 گروه‌های جدا هستند. جمعاً 9 بردار یکتا وجود دارد؛ Confidence نیز در تشخیص Aliasها لحاظ شده است.
- Zero Switchهای V2/Direct/V3 و یکسانی P1/P2 با R1 حفظ شده‌اند. نام‌های متفاوت به Fit تکراری منجر نشده‌اند.

## وضعیت تحویل

تمام Fitهای مجاز همین بسته اجرا یا با مدرک Reuse شده‌اند. کل مطالعه همچنان PARTIAL_BLOCKED است و روش‌های فاقد ورودی اصیل برای تکمیل به مجوز و شواهد مستقل نیاز دارند. هیچ Label، Prompt یا Policy تغییر نکرد، هیچ API اجرا نشد و هیچ دادهٔ خصوصی یا Prediction نودبه‌نود در گزارش‌ها قرار ندارد. تغییرات قبلی PROJECT_STATE و GraphScope حفظ شده‌اند؛ فقط فایل‌های همین Slice برای Commit انتخاب می‌شوند.
