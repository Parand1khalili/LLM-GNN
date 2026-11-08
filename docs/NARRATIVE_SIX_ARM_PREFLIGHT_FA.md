# پیش‌پرواز شش‌Arm — 2026-11-08

Manifest خصوصی شامل2520 درخواست Draft است؛ هیچ درخواست پولی اجرا نشده است.
SHA `d5cddb404c55e03cd3356aa01fc2958c4a73895809e651c728b1efcc2a5f0ae1`

B1 و v0 از Promptهای Frozen اصیل خوانده شدند. A/B عین Freeze قبلی‌اند.
C/D فقط دستور را تغییر می‌دهند و همان Bundle، ترتیب همسایه، truncation،
taxonomy و schema سه answer/confidence را دارند. سقف هر چهار Arm برابر4096
توکن cl100k_base است. این شمار، Tokenization تأییدشدهٔ Provider نیست.

|Arm|Calls|Input prompt tokens برای سه نمونه|Max prompt tokens|
|---|---:|---:|---:|
|B1|420|122622|748|
|v0|420|234255|1046|
|A|420|475641|1737|
|B|420|493701|1780|
|C|420|486141|1762|
|D|420|486141|1762|

Provider موجود GapGPT با endpoint https://api.gapgpt.app/v1/chat/completions
و مدل درخواستی gpt-6-luna است. alias و revision گزارش‌شدهٔ تاریخی
gpt-6-luna-2026-09-22 تنها شناسه‌های مطرح موجودند؛ دسترسی فعلی احراز نشده است.
طرح decoding جدید temperature1/n1/output4096 مشترک برای همهٔ Armها پیشنهاد شده؛
این نسبت به B1/v0 تاریخی با temperature0.7 یک تغییر اجرای صریح است.
قبل از اجرا مالک باید مدل، تنظیمات و cap را تأیید کند.

صفحهٔ https://gapgpt.app/platform-v2/pricing در بررسی فعلی فقط Loader داد.
نرخ‌های تاریخی مالک0.10/M input و0.50/M output تأیید فعلی نشده‌اند.
با این فرض‌ها و128 توکن framing فرضی برای هر Call، سناریوی512 output/call
حدود0.9072261 دلار است. رزرو32768 input و4096 output در هر Call،
13.418496 دلار برای2520 Call می‌شود؛ هر Arm2.236416 دلار.
این رزرو تضمین صورتحساب یا اثبات سقف واقعی Provider نیست.
سقف پیشنهادی15 دلار است و هنوز تصویب نشده است.

Smoke test از دو Target با ترتیب SHA256 رشتهٔ six-arm-smoke-v1|node_id انتخاب
می‌شود؛ شش Arm و سه نمونه یعنی36 Call، داخل سقف کل2520. رزرو سناریویی آن
0.1916928 دلار است. خروجی و هزینهٔ نامتعارف پیش از Scale نیازمند بازبینی مالک است.

کلید در Process موجود نبود. مالک باید GAPGPT_API_KEY را در محیط محلی یا
ورودی مخفی Terminal تنظیم کند؛ هیچ کلید یا بخشی از آن به چت فرستاده نشود.
در این مرحله هیچ کلیدی خوانده یا ذخیره نشده است.

وضعیت فعلی BLOCKED_MODEL_PRICING_AND_SPENDING_APPROVAL است. این ماژول
فقط Prompt و Manifest/Cost preflight می‌سازد؛ Runner پولی، Retry، Ledger
اجرا، Parse پاسخ واقعی و Prediction Freeze هنوز آماده و تأیید نشده‌اند.
اجرای مجوزدار آینده باید این مراحل را با تست‌های Mock تکمیل کند.
Historical verifier schema با schema طبقه‌بندی top3 متفاوت است و نباید
از strict_envelope مخصوص Rich Evidence برای این خروجی استفاده کرد.
Voting موجود annotation/voting.py باید در تمام Armها یکسان اعمال شود.

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.annotation.six_arm_preflight
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_six_arm_preflight.py -v
```

Primary مقایسه paired B−A روی140 Target است. GT تنها بعد از Prediction Freeze
در Evaluator جدا باز می‌شود. نتیجه، Accuracy، Usage واقعی، هزینهٔ واقعی و
GT Evaluation فعلاً NOT_RUN هستند. هیچ GCN اجرا نمی‌شود.
