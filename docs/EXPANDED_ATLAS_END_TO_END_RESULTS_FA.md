# Expanded Atlas End-to-End — پیش‌پرواز خصوصی و توقف مجاز

LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT

## نتیجهٔ ممیزی

Freeze اطلس و ترتیب انتخاب
`6b624adac49e9a8e3a78de6d7628e4fc1b654b21b5307a33ebd9b5ef4a007fe0`

رسید ممیزی GT-free
`786d4e11d36f6a8ab6a061d63ba9ff5fded4f85cdb107f1d9fdc02a1bbd1eb77`

هر دو اجرای واقعی R0 و R1-v1 با correction_features.extract_run بازپخش شدند.
این بررسی 129 Intent تاریخی، شامل دو Rejection اصیل، را با Wire، متن، Payload،
Dependency، Context، Hash پاسخ، Parser و L1 تطبیق داد. هیچ نتیجهٔ جدید Agent تولید نشد.

| وضعیت روی 37 نود منتخب جدید | تعداد |
|---|---:|
| نود دارای پاسخ در حداقل یکی از دو اجرای معتبر |32|
| نود بدون پاسخ در این دو اجرای کامل و سازگار |5|
| Blind قابل Reuse با هویت کامل فعلی |0|
| Blind موجود ولی متعلق به Context دیگر |32|
| Blind گمشده در این دو اجرای سازگار |5|

صفر Reuse ناشی از فقدان محتوا برای تمام نودها نیست. در قرارداد فعلی،
gateway_continuation.identity صریحاً context_sha256 را وارد هویت می‌کند.
gateway_run.gateway_context شامل Router، فهرست مرتب انتخاب و inputs_context_sha256
است. تغییر ده انتخاب، Context را تغییر می‌دهد. بنابراین حتی Payload و متن
برابر، هویت کامل فعلی را برابر نمی‌کند. بازاستفادهٔ بین Contextها به تعریف و
تصویب یک amendment مستقل نیاز دارد. در این Slice قرارداد Reuse تغییر نکرد.

Comparison فقط پس از پاسخ واقعی Blind قابل تعیین است. هویت آن علاوه بر
Context به digest همان پاسخ Blind و کلاس Blind وابسته است. تعداد دقیق
Comparisonهای آینده پیش از اجرای Blind قابل تعیین نیست. پاسخ‌های قدیمی
نباید به پاسخ Blind جدید متصل شوند. فایل‌های legacy یا partial با schema،
Prompt و قرارداد متفاوت برای این آزمایش مجاز فرض نشده‌اند.

## قرارداد علمی و Router

R1 مورد استفاده نسخهٔ بازسازی‌شدهٔ sara.router.r1_candidate.v1 است.
انتخاب پایه روی همین داده با بستهٔ منجمد اجرای واقعی R1 تطابق داشت.
اطلس قدیمی 24/37 و اطلس گسترش‌یافته 27/37 نود دارای خطای حداقل یکی از دو
Baseline انتخاب کردند. اشتراک 27 نود است. NO_MATCH از30 به18 کاهش یافت.
این اعداد از تشخیص پسینی قبلی نقل شده‌اند؛ در این ممیزی GT باز نشد.

## دامنهٔ درخواست برای تأیید مالک

با اجرای قرارداد هویت کامل فعلی، 37 Blind تازه و صفر تا37 Comparison شرطی
لازم است. حداکثر74 Generation. شمار Comparison و هزینهٔ واقعی هنوز نامعلوم است.
فقط Blind معتبر، L1 PASS و non-abstaining می‌تواند Comparison داشته باشد.

تنظیم موجود سقف اعلامی input32768 و output4096 دارد. با نرخ‌های موقت مالک
0.10 دلار/M input و0.50 دلار/M output، برآورد رزرو هر Call برابر0.0053248 دلار،
برای37 Blind برابر0.1970176 و برای74 Call برابر0.3940352 دلار است.
این مقادیر Tokenization واقعی یا سقف تضمینی صورتحساب نیستند. اعتبار فعلی مدل،
Privacy/Retention، بودجهٔ دلاری و ارسال مقاله‌ها باید در تأیید محلی ثبت شوند.
اعتبار یا موجودی فعلی Provider با شبکه بررسی نشده است.

## وضعیت مراحل بعد

| مرحله | وضعیت |
|---|---|
| ممیزی اصالت اجرای کامل R0/R1 |PASS|
| ثبت خصوصی محدودیت Reuse |PASS|
| ارسال Agent برای اطلس جدید |BLOCKED_PENDING_APPROVAL|
| L1/L2 و خروجی Automated V1 جدید |NOT_RUN / L2 NOT_ASSESSED|
| Freeze بردار آموزشی جدید |NOT_RUN|
| Raw Correct/Wrong/Abstain و Fix/Harm جدید |NOT_RUN|
| GCN و Controls جدید |BLOCKED_INDEPENDENT_ADMISSION_REQUIRED|

مراجع GCN تاریخی Sensitivity/Natural/WCE/noPS عبارت‌اند از
Automated V1+R1 برابر74.3769%، C برابر73.7850% و Narrative برابر73.1659%.
برای اطلس جدید Accuracy یا Macro-F1 وجود ندارد.

پس از تأیید API، اجرای انتخاب Frozen و Freeze خروجی Automated V1 مقدم بر
درخواست Admission مستقل است. کنترل Router-only باید همان حذف نودهای Routed
از Baseline Agreement را اجرا کند. اگر Automated V1 هیچ پیشنهاد پذیرفته‌ای
نداشت، کنترل و Treatment احتمالاً Alias می‌شوند؛ هم‌ارزی باید با Fingerprint
کامل ثابت شود. تعریف دقیق Control هم‌پوشش و هم‌تعدادکلاس هنوز Freeze نشده
و باید GT-free پیش از ارزیابی تازه ثبت شود.

## بررسی‌های اجراشده

Replay هر دو journal اصلی و continuation شامل129 Intent با127 Completed و2 Rejected بود.
extract_run شمار67 برای R0 و62 برای R1 را الزام می‌کند.
بررسی Context، Request، Response و Dependency در همین Replay اجرا شد.
آموزش، درخواست شبکه و GT Evaluation جدید صفر هستند.

کار تا مانع مجوز API پیش رفته است. نتیجهٔ Router برای اثبات بهبود Label یا
GCN کفایت ندارد. گزارش و Artifactهای ممیزی محلی‌اند؛ Commit و Push انجام نشد.


## تأیید مالک و بررسی شروط اجرای تازه

مالک حداکثر74 درخواست و1 دلار را تأیید کرد. ارسال داده‌های همان37 نود نیز تأیید شد. این تأیید به بسته‌های Admission آموزشی قبلی افزوده نشد.

Config تاریخی صریحاً retention_status=GATEWAY_RETENTION_NOT_VERIFIED دارد. نرخ‌ها user-declared هستند. صفحهٔ رسمی pricing و privacy در بررسی عمومی فقط loader برنامه را برگرداندند؛ endpoint عمومی نیز از ابزار وب قابل خواندن نبود. نرخ فعلی، شرایط نگهداری، دسترسی فعلی مدل و سقف واقعی token احراز نشدند. طبق بند3 و5 تأیید مالک، اجرای زنده پیش از dispatch مسدود شد. هیچ Intent ارسال تازه ایجاد نشد.

قواعد کنترل‌ها پیش از هر GT تازه ثبت شدند. SHA-256 d937b78f89ce12aa07700e87bb53626f05b5c669bee5b23904d7ac41a0babc8e

Router-only تمام نودهای منتخب را Abstain و توافق واجدشرایط Baseline خارج انتخاب را حفظ می‌کند. کنترل class-count-matched از توافق‌های معتبر Baseline برای هر کلاس به تعداد Treatment نمونه می‌گیرد، با ترتیب SHA256 رشتهٔ ثابت expanded-atlas-control-v1|node_id. کمبود یک کلاس باعث BLOCKED می‌شود. Rule انتخاب مهندسی ازپیش‌ثبت‌شده است؛ Outcome در آن دخالت ندارد. Mask و شمار کلاس نهایی پس از Freeze Treatment ساخته خواهند شد.

برای رفع مانع، مستند رسمی قابل بررسی دربارهٔ مدل دقیق، تعرفه و token/reasoning billing و شرایط retention همین حساب لازم است. هیچ درخواست آزمایشیِ هزینه‌دار برای کشف این موارد ارسال نشد. Spec/Fit تازه تا مشخص‌شدن بردار نهایی قابل شمارش دقیق نیست.


## اجرای واقعی و اصلاح خطای Wrapper

16 درخواست واقعی؛15 Completed و1 Rejected با L1_QUOTE_NOT_FOUND؛0 UNCERTAIN. Blind Completed=9 وComparison Completed=6. Gateway پیش از خطای Wrapper Summary را در journal ذخیره کرده بود. Wrapper ذخیرهٔ اضافی در والد فاقد ACL خصوصی انجام می‌داد؛ این ذخیره حذف و --inspect-only اضافه شد. بازخوانی Summary با Hash ad478248297e04f26ceb55fae41655a6364d8a047a7c63f71b6cd904c8f87163 موفق بود. هیچ درخواست مجدد ارسال نشد. Usage گزارش‌شده فقط برای Completedها input23497/output7346 و برآورد0.0060227 دلار است؛ هزینهٔ پاسخ ردشده و صورتحساب واقعی نامعلوم‌اند. اجرای کامل37 نود و ارزیابی GT جدید انجام نشده است.


## ممیزی مستقل Comparison ردشده

Hash پاسخ خصوصی تأیید شد. هر سه supporting quote و تک counter quote زیررشتهٔ دقیق target.text هستند. supporting_evidence[2] به طول198 با حرف W شروع و با ASCII double quote پایان می‌یابد. quote_for_matching هر وجود علامت نقل‌قول در یکی از دو انتهای رشته را wrapper می‌پندارد؛ بنابراین پیش از جست‌وجوی substring خطا می‌دهد. بازپخش Validator همین L1_QUOTE_NOT_FOUND را بازتولید کرد. Fixture مستقلِ جمله‌ای که با اصطلاح داخل نقل‌قول پایان می‌یابد نیز همین رفتار را بازتولید کرد. این ردشدن ناشی از تغییر واژه توسط مدل نیست. نتیجهٔ اصلی REJECTED و L1 تاریخی حفظ شدند.

Gateway فعلی تمام REJECTEDها را توقف سراسری می‌داند. ادامهٔ مستقل نیازمند مسیر opt-in برای بازخوانی و راستی‌آزمایی Receipt ردشده، حفظ دلیل اصلی و عبور به نود بعدی است؛ UNCERTAIN و خرابی Integrity باید توقف بمانند. این اصلاح هنوز پیاده‌سازی/تست نشده است. هیچ Call تازه ارسال نشد. کوچک‌ترین اصلاح احتمالی L1 در Slice جدا این است که پیش از تفسیر wrapper، تطابق عین رشته بررسی شود؛ در این اجرا مجوز تغییر L1 وجود ندارد.


## اصلاحیهٔ نسخه‌دار L1

نسخه sara.l1.source_exact_first.v2 با ContextVar صریح EXACT_FIRST اضافه شد. پیش‌فرض False رفتار تاریخی را حفظ می‌کند. در حالت جدید، اگر رشتهٔ کامل عیناً در منبع باشد همان رشته استفاده می‌شود؛ در غیر این صورت قاعدهٔ wrapper تاریخی اجرا می‌شود. دو تست مثبت/منفی و بازگشت Context به رفتار تاریخی PASS شدند. بازپخش مستقل تمام16 پاسخ موجود زیر نسخه جدید16 PASS داشت؛15 Completed قبلی حفظ اعتبار داشتند و مورد REJECTED فقط در ارزیابی مجزا PASS شد. رسید تشخیصی f10588625c0ced43a7aba341595f875ef642f3cf4c38b35a8df7104495b4b296، بدون تغییر Ledger و بدون Admission آموزشی. اصلاح Safe Continuation و تست‌های Resume/Integrity هنوز تکمیل نشده‌اند. هیچ Call تازه‌ای اجرا نشده است.
