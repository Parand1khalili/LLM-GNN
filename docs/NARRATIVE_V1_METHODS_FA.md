# Narrative v1 — روش و ممیزی آفلاین

هدف، مقایسهٔ v1-A و v1-B با شواهد برابر است. هیچ GT، Outcome، پاسخ Agent یا 38 خطای مشترک در انتخاب همسایه و ساخت Prompt خوانده نشد.

|Arm|متن همسایه|ساختار|دستور|وضعیت|
|---|---|---|---|---|
|B1 Frozen|ندارد|ندارد|Wrapper تاریخی|مرجع تاریخی|
|Narrative v0 Frozen|یک Representative با خلاصهٔ تعداد حمایت معنایی|اتصال/عدم اتصال زوج‌های منتخب|Wrapper تاریخی و اولویت Target|مرجع تاریخی|
|v1-A|تا4 متن مستقل اصیل|Degree و اتصال واقعی زوج‌ها|دستور کوتاه اولویت Target|Prompt Frozen؛ NOT_RUN|
|v1-B|دقیقاً همان بستهٔ A|دقیقاً همان A|ارزیابی مستقل حمایت/تعارض/ابهام، Topic و Auxiliary Method|Prompt Frozen؛ NOT_RUN|

## قرارداد و منابع

تاریخی Consensus سقف256 توکن برای Representative و prose حمایت داشت؛ Narrative v0 سقف320 برای context ساختاری دارد. Topology و شمار حمایت، متن مستقل همهٔ همسایه‌ها نیستند. descriptors معتبر ممکن است در topology آمده باشند. این ممیزی از موجودبودن اطلاعات، استفادهٔ واقعی LLM را استنتاج نمی‌کند.

متن اصلی از فهرست raw_text گراف با Hash ثابت، فقط با خواندن ایستای opcodeهای Pickle و بدون اجرای Pickle استخراج شد. فقط Storage یال1 خوانده می‌شود؛ y و Label Storage خوانده نمی‌شوند. هر2708 متن با ترتیب همان فایل نگهداری می‌شود و تمام140 متن Target دقیقاً با ورودی Frozen برابر بودند. هیچ متن یا خلاصه‌ای تولید نشده است.

همسایه‌ها ابتدا با ترتیب Frozen تاریخی و سپس ID صعودی بقیهٔ همسایه‌های مستقیم انتخاب شدند. متن خالی کنار گذاشته می‌شود. K=4 و سقف هر snippet برابر128 توکن است. prefix نویسه‌ایِ اصیل با شمارش Tokenizer انتخاب می‌شود؛ هیچ متن Target حذف یا کوتاه نمی‌شود. دو Arm یک Bundle مشترک دارند، فقط instruction فرق دارد. سقف مشترک4096 است؛ padding ندارند. Source SHA و Snippet SHA جدا ثبت می‌شوند.

Tokenizer همان cl100k_base با cache محلی Hash-pinned است؛ دانلود شبکه‌ای انجام نمی‌شود. شمار توکن دقیق برای همین tokenizer است؛ هم‌ارزی با Tokenizer Provider اثبات نشده است. Framing سرویس و output در این شمار نیست.

Wrapper تاریخی taxonomy هفت‌کلاسه و سه حدس answer/confidence با مجموع Confidence100 را عیناً به هر دو Prompt می‌افزاید. هیچ فیلد Reasoning جدید به parser اضافه نشد. Model تاریخی gpt-6-luna، temperature0.7، n1 و سه نمونهٔ مستقل بود. دسترسی فعلی alias و سازگاری0.7 تأیید نشده؛ اجرای آینده نیازمند مدل/Revision و decoding مشترک و مجوز جدا است.

## آمار واقعی آماده‌سازی

140 Target؛ Degree از1 تا78؛ هیچ Target منزوی در این Cohort نبود. رفتار منزوی با fixture آزموده شد. 69 Target چهار،29 مورد سه،23 مورد دو و19 مورد یک متن همسایه دارند. از428 snippet انتخاب‌شده،296 مورد با سقف128 توکن کوتاه شدند. تاریخی23 Target دو همسایه،98 مورد سه و19 مورد یک همسایه انتخاب کرده بود؛ متن مستقل Representative برای هر140 موجود بود. مجموع زوج‌های تاریخی166 متصل و151 نامتصل بود.

|Prompt|Min tokens|Mean tokens|Max tokens|
|---|---:|---:|---:|
|v1-A|418|1132.4786|1737|
|v1-B|461|1175.4786|1780|
|v0 historical|246|در این گزارش محاسبه نشده|1046|

B نسبت به A دقیقاً43 توکن دستور بیشتر دارد. اطلاعات و truncation مشترک پیش از افزودن دستور آماده شدند. شواهد نمی‌توانند Target یا Schema را جابه‌جا کنند؛ عبور از cap باعث Fail-closed می‌شود. مقایسهٔ v0 با A هم نمایش و هم مقدار اطلاعات را تغییر می‌دهد؛ بهبود احتمالی را نمی‌توان فقط به instruction نسبت داد.

Spec SHA c4c5a61670f6aacb95a66d20677522f6bf224bfc463c7a209ff920b9cc68e1c4

Prompt Freeze SHA 916ef67f164202861dfb16e7144ad99d28f82c84a71e9b4d3a110fa3d0a40900

## اجرای مجدد و بررسی

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.annotation.narrative_v1
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_narrative_v1.py -v
```

خروجی خصوصی CAS در .local_artifacts/narrative_v1 است؛ تکرار بایت‌برابر همان Artifact را Readback می‌کند. تغییر Source نسخهٔ Freeze جدید می‌دهد و قبلی overwrite نمی‌شود. Promptها، IDs، Hashها، token counts، truncation و skeleton درخواست در همان Artifact هستند. گزارش عمومی reports/narrative_v1_prompt_audit.json فقط Aggregate و fingerprint دارد و قرارداد داده برای GraphScope است؛ Frontend تغییر نکرد.

## پروتکل ارزیابی آینده

معیار اصلی از پیش تعیین‌شده، اختلاف Accuracy کل140 نود B−A با مقایسهٔ paired است. معیارهای ثانویه شامل Class-wise PRF، Confusion، اصلاح/تخریب، Degree، دسترسی متن، هزینه و پراکندگی سه نمونه‌اند. خروجی فعلی پیش‌بینی یا نتیجهٔ LLM نیست. ارزیاب GT-only تنها پس از دریافت و Freeze پیش‌بینی‌های واقعی اجرا می‌شود. گروه خطای مشترک و Homophily فقط strata تشخیصی پسینی‌اند. هیچ Threshold یا Prompt با آن‌ها تنظیم نمی‌شود.

برای A/B سه نمونهٔ مستقل در هر Target/Arm یعنی840 درخواست آینده؛ مقایسهٔ contemporaneous چهار Arm حداکثر1680 درخواست است. این شمار مجوز هزینه نیست. تعرفه، output caps، Request settings، حریم خصوصی و Spending approval باید پیش از اجرا بررسی شوند. Downstream نیازمند Admission، Confidence provenance و Config matched مستقل است.

## Verification و محدودیت

6 تست Builder،1 Tokenizer و6 CLI/GT-isolation پاس شدند. هیچ API، Training یا GT Evaluation اجرا نشد. فایل‌های تاریخی Narrative v0 تغییر نکردند. تست‌ها corrupt hash، mismatch Target، همسایهٔ نامعتبر، missing text، isolation، truncation، cap، برابر بودن Bundle و ثابت‌بودن wrapper را بررسی کردند. Full Suite محلی اجرا نشد.

الگوریتم واژگانی انتخاب همسایه یک انتخاب مهندسی از پیش تعیین‌شده است؛ همنوعی کلاس و relevancy معنایی تضمین نمی‌شود. text موجود را original stored paper text می‌نامیم؛ کامل‌بودن Full Paper ادعا نمی‌شود. provenance محدود Encoder در این مرحله برای انتخاب متن استفاده نمی‌شود. تاریخی v0 را از Template و Receipt احراز کردیم؛ استفادهٔ مدل از هر بخش قابل مشاهده نیست.


یک بازاجرای Tempfile داخل sandbox Windows با WinError5 مواجه شد؛ همان6 تست بدون تغییر در محیط مالک PASS شدند. آماده‌سازی واقعی با socket.connect مسدود نیز همان Freeze را بازتولید کرد. فایل دادهٔ عمومی فقط آمار Aggregate دارد.
