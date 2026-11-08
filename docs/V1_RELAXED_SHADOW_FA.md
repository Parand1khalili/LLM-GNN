# V1-Relaxed Shadow

Policy `sara.arbitration.evidence_gated_third_class.v1` مستقل از Automated V1 است.
Binding نامعتبر، فاز مفقود/Rejected/UNCERTAIN یا L1 نامعتبر به REJECT_INVALID_EVIDENCE می‌رسد.
Abstention یا اختلاف کلاس به ABSTAIN می‌رسد. توافق معتبر دو فاز روی کلاس سوم،
PROPOSE_CLASS_SWITCH می‌دهد. توافق روی کاندیدای تاریخی بردار V1 را حفظ می‌کند.
Warning، Counter-evidence، Uncertainty، Topic و اشتراک Quote ثبت می‌شوند؛ در این
نسخه مانع Proposal موقت نیستند. L2 همیشه NOT_ASSESSED و Confidence کلاس سوم
ناموجود است. هیچ Proposal مجوز آموزش ندارد.

تابع Pure سازگاری Binding ارائه‌شده را بررسی می‌کند؛ احراز اصالت Receipt برعهده
adapter است که هر65 Intent را با Freeze اصلی دوباره تطبیق می‌دهد. Rejected
اصلی بازنویسی یا معتبر فرض نمی‌شود.

Freeze قبل از GT
`771eccefde1845f7d6beb53c3aff4bb5e792e0b524f124c792d700ca4c819cc1`

GT-only result
`370958326295acafda085c003efbe993f2288e07b8b8bf7a1da9b5706317f6f6`

|روش|درست|غلط|امتناع|
|---|---:|---:|---:|
|C|72|21|47|
|Expanded V1 / Router-only|67|12|61|
|V1-Relaxed|69|15|56|
|Coverage no-Agent|67|17|56|
|Old V1 R1|67|11|62|

پنج Proposal کلاس سوم شامل2 درست و3 غلط بود؛ هر پنج مورد نسبت به Expanded V1
از Abstention خارج شدند. پوشش84/140 و Selective Accuracy برابر69/84 است.
فایل reports/v1_relaxed_aggregate.json شامل Class-wise metrics، Confusion،
مقایسه‌های زوجی و تشخیص گروه خطای مشترک است. دادهٔ نودبه‌نود خصوصی می‌ماند.

کنترل Coverage همان Train IDs را دارد و رأی Baseline با Confidence بالاتر را
انتخاب می‌کند؛ Tie به B1 می‌رسد. کنترل تعدادکلاس از توافق‌های C با ترتیب Hash
ثابت و شمار کلاس‌های Treatment ساخته می‌شود؛ کمبود کلاس BLOCKED است.
Fingerprint بردارها شامل IDs، Classes، Confidence و Provenance است. هنوز
Spec/Fit با Runtime آموزشی ساخته نشده؛ Dedup آموزشی نهایی انجام نشده است.

CE در وضعیت Draft است. WCE برای کلاس سوم فاقد Confidence معتبر است و نیاز
به پروتکل مستقل دارد. Admission، ممیزی Split/Features و مجوز Training لازم‌اند.
هیچ Training یا API جدیدی اجرا نشد.

```powershell
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.v1_relaxed_shadow
.venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.v1_relaxed --shadow-sha256 771eccefde1845f7d6beb53c3aff4bb5e792e0b524f124c792d700ca4c819cc1
```

LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT
