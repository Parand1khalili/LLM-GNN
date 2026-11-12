# نتیجهٔ نهایی SARA-Lite v1

LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT

## پروتکل و اجرا

یک Reviewer، Router موجود R1-v1 با فرمول و Tie-breaking ثابت و بودجهٔ ۳۷، Baselineهای هم‌زمان B1/Narrative v0 و پیش‌فرض Narrative استفاده شد. Confidence در Routing نقشی ندارد. هیچ GT، Homophily یا Outcome برای انتخاب نود، Prompt یا Policy استفاده نشد. قواعد و کنترل‌ها پیش از GT منجمد شدند. Quote فقط با متن Target تطبیق دقیق دارد؛ صحت Quote معادل تأیید معنایی نیست. L2 همچنان NOT_ASSESSED است.

۳۷ درخواست واقعی شامل دو Smoke و ۳۵ درخواست Full ثبت شد؛ هیچ Retry یا درخواست جدید در این ممیزی ارسال نشد. ۲۷ پاسخ COMPLETED و ۱۰ پاسخ REJECTED؛ Dispatch مبهم یا درخواست ارسال‌نشده وجود ندارد. ۲۲ KEEP، چهار SWITCH، یک ABSTAIN و ۱۰ UNAVAILABLE ثبت شد.

## خطاهای قرارداد

۹ پاسخ HTTP200 شناسهٔ openai/gpt-6-luna داشتند که خارج از دو شناسهٔ دقیق مجاز بود. هم‌ارزی این Alias به‌طور مستقل احراز نشده و قرارداد Identity پس از مشاهدهٔ پاسخ‌ها تغییر نکرد. یک پاسخ دیگر SOURCE_QUOTE داشت. این‌ها به PASS تبدیل یا دوباره درخواست نشدند. مجموع شناسه‌های گزارش‌شده: ۲۸ gpt-6-luna و ۹ openai/gpt-6-luna. همهٔ Receiptها، Binding، Hash و ۳۷ Response ID یکتا بررسی شدند. جزئیات Node-level و پاسخ‌های خام فقط محلی و خصوصی‌اند.

## Hashهای قابل بازتولید

Protocol: `9a2258be64b73583b1c4fd014ca7caa1aab179f90b909fc24e222244f0d7dadd`

Manifest: `dea21474fc5027237f3ea8e69999eb98dd18e7ebb40e0ead18400600f2e0088a`

Prediction freeze: `00daac8087163980123bdcb4796f99c4bb36854ec2382876be4dc75ee6390db5`

GT-only evaluation: `71e62298fd407341d7fbba616be54fc9b9ff62d49f85af812891586006ca43f4`

Approval: `d72ed51166bdcde38ebf474639fefcbd12be349518df1b5f738b058d7713f387`

## نتایج روی Cohort ثابت ۱۴۰

|Arm|درست|غلط|Abstain|Unavailable|Coverage %|Accuracy کل %|Selective Accuracy %|Macro-F1|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|Narrative v0|103|37|0|0|100.00|73.57|73.57|0.7355|
|Router-only|84|19|37|0|73.57|60.00|81.55|0.6799|
|SARA-Lite|96|33|1|10|92.14|68.57|74.42|0.7169|
|Exact-mask no-Agent|96|33|11|0|92.14|68.57|74.42|0.7135|
|Class-count no-Agent|95|34|11|0|92.14|67.86|73.64|0.7036|

Accuracy کل=Correct/140؛ Selective Accuracy=Correct/Accepted. Abstention و Unavailable نه Correct هستند نه Wrong. Macro-F1 هفت‌کلاسه است؛ Confusion هفت‌درهشت با ستون آخر فاقد Prediction است. Missingness در Recall، False Negative محسوب می‌شود. در خروجی عمومی Strata، فیلد unavailable تابع عمومی score تمام موارد فاقد Prediction را دربرمی‌گیرد؛ تفکیک عملیاتی Abstain/Unavailable در جدول اصلی بالاست.

## ارزش افزودهٔ Agent

مقایسهٔ اصلی روی Mask دقیقاً مشترک C و D با ۱۲۹ نود: دو Wrong→Correct و دو Correct→Wrong؛ Net=0 و اختلاف Accuracy=0.000pp. چهار SWITCH شامل دو درست و دو غلط بود. یک SWITCH کلاس سوم بود و درست بود. اختلاف Macro-F1 برابر +0.00342 به سود Lite است؛ این تغییر کوچک اکتشافی، تأیید ایمنی یا برتری تعمیم‌پذیر نیست.

در مقایسه با Router-only، Lite تعداد ۲۶ Label اضافه نگه داشت: ۱۲ درست و ۱۴ غلط. بنابراین اختلاف خام تعداد Correct، اثر Coverage را هم دربرمی‌گیرد و شاهد مستقل اصلاح کلاسی نیست. Router-only فقط ۱۰۳ Label با Selective Accuracy=81.55% دارد؛ Lite با ۱۲۹ Label، 74.42%.

C نسبت به Narrative کامل هفت Correct کمتر دارد؛ حذف ۱۱ Prediction که در Baseline شامل هفت درست و چهار غلط بودند، با Net صفر Switchها این اختلاف را توضیح می‌دهد. یک حذف ABSTAIN مدل و ده مورد نقص اعتبار قرارداد هستند؛ این ده مورد را Abstention هوشمند مدل تلقی نکنید.

کنترل E همان تعداد Label و شمار کلاس‌های Lite را دارد، اما IDs متفاوت‌اند؛ C یک Correct بیشتر از E دارد. این اختلاف، تخمین علّی اثر Reviewer نیست. کنترل پولی Self-consistency سازگار موجود نبود و اجرا نشد.

## Router و Homophily

Router در ۳۷ هدف منتخب ۱۸ خطای Narrative پیدا کرد (48.65%)؛ در ۱۰۳ هدف انتخاب‌نشده ۱۹ خطا بود (18.45%). این Error-enrichment پسینی است؛ Rule یا Budget بر اساس آن تغییر نکرد.

در ۱۲۲ هدف هموفیلیک، Narrative تعداد ۹۵ و Lite تعداد ۸۹ Correct داشتند؛ کنترل D نیز ۸۹. در ۱۱ هدف هتروفیلیک، Narrative هفت و Lite/D شش Correct داشتند. در هفت هدف مختلط همهٔ این Armها یک Correct داشتند. دادهٔ مفقود، اندازهٔ کوچک گروه‌ها و وابستگی گراف، نتیجه‌گیری علّی را محدود می‌کنند.

## هزینه و منابع

سقف مصوب USD0.25 بود. Usage تمام ۳۷ پاسخ، شامل ردشده‌ها: Input=40194 و Output=13387. با نرخ منتشرشدهٔ Input=$0.10/M و Output=$0.50/M برآورد کل $0.0107129 است. Usage فقط ۲۷ پاسخ معتبر Input=29566 و Output=9120 و برآورد $0.0075166 بود؛ این دو جمع را مخلوط نکنید. هزینهٔ واقعی صورتحساب UNKNOWN است. Reasoning زیرمجموعهٔ Output است و دوباره قیمت‌گذاری نشده است.

برآورد هزینه به‌ازای هر Review ارسال‌شده حدود $0.000290، هر پاسخ معتبر $0.000397 و هر Label پذیرفته‌شده در میان نودهای Reviewشده $0.000412 است. این مقادیر تخمینی‌اند و نسبت به کل ۱۲۹ Label که بیشترشان Review نشده‌اند بیان نشده‌اند.

## مقایسهٔ تاریخی و محدودیت

Expanded V1 تاریخی با Router-only بردار یکسان داشت؛ V1-Relaxed تاریخی پنج Third-class با دو درست و سه غلط داشت. Lite در اجرای جدید چهار Switch معتبر با Net صفر داشت. Baseline، Router selection، Context، زمان و تعداد Callها یکسان نیستند؛ این‌ها مقایسهٔ کنترل‌شدهٔ مستقیم با یکدیگر یا با GCN تاریخی نیستند. هیچ GCN Accuracy برای Lite تولید نشده است.

این اجرای SARA-Lite از نظر ارسال همهٔ ۳۷ درخواست کامل است، اما Freeze تحلیلی به‌دلیل ۱۰ پاسخ خارج از قرارداد PARTIAL است. اثر نامعتبرشدن ۹ پاسخ مدل، مانع ادعای قطعی دربارهٔ توانایی ذاتی Reviewer می‌شود. با همین قرارداد واقعی و پاسخ‌های پذیرفته‌شده، شواهدی از سود خالص اصلاح کلاس نسبت به کنترل هم‌Mask به دست نیامد.

این آخرین آزمایش معماری Agent در Scope فعلی است: Prompt یا Threshold تغییر نمی‌کند؛ Lite v2 یا Gate جدید برای نجات نتایج ساخته نمی‌شود. توصیهٔ قابل دفاع، ثبت نتیجهٔ صفر خالص، گزارش محدودیت Identity و تکمیل پایان‌نامه/GraphScope است. تأیید مستقل در Dataset دیگر نیازمند پروتکل و مجوز جدا است؛ توجیهی برای Admission خودکار یا Training فعلی وجود ندارد.

## Admission و Verification

تمام Labelها Shadow هستند و NOT_ADMITTED باقی می‌مانند. Confidence Switchها موجود نیست؛ WCE نیازمند پروتکل Missing-confidence مصوب مستقل است. CE نیز به Admission، بررسی Features/Split و مجوز Training مستقل نیاز دارد. هیچ GT وارد Training یا Policy نشد.

۳۶ تست مرتبط Synthetic/Baseline/Recovery پاس شدند. Readback مستقل CAS، شمار Correct/Covered، جمع Confusion و بازاجرای آفلاین Receipt/Vector پاس شدند. Full Suite در این Slice اجرا نشد. هیچ پاسخ خصوصی، Node-level GT یا کلید در خروجی عمومی نیست.

## بازتولید فقط آفلاین

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_sara_lite*.py" -v
.venv\Scripts\python.exe -B -m llmgnn_sara.annotation.sara_lite_freeze
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.sara_lite --freeze 00daac8087163980123bdcb4796f99c4bb36854ec2382876be4dc75ee6390db5
```

فرمان API را دوباره اجرا نکنید. Rawها، نگاشت Node، جزئیات ردها و Diagnostic GT فقط در .local_artifacts/sara_lite_v1 هستند. جداول Class-wise/Confusion/Strata در reports/sara_lite_evaluation.json؛ جدول اصلی در reports/sara_lite_metrics.csv و ممیزی هزینه/خطا در reports/sara_lite_execution_audit.json قرار دارند.
