# SARA-Lite v1 — پروتکل GT-free پیش از اجرای پولی

وضعیت: PREPARED / NOT_RUN. هیچ نتیجهٔ Reviewer، Freeze خروجی یا GT Evaluation جدیدی وجود ندارد.

پرسش اصلی: آیا یک Review نسبت به نگه‌داشتن Narrative روی همان Mask ارزش افزوده دارد؟
Baselineها B1 و Narrative v0 هم‌زمان از Freeze معتبر شش‌Arm هستند؛ هیچ نتیجهٔ GT در آماده‌سازی خوانده نشد. Hash تمام فایل‌های اجرای قبلی با Snapshot ثبت‌شده تطبیق داده شد.

- Router: پیاده‌سازی موجود `sara.router.r1_candidate.v1`، همان فرمول Lexical و Tie-breaking، بودجهٔ ۳۷. این اجرا با Baselineهای هم‌زمان است و همان انتخاب تاریخی معرفی نمی‌شود. Router به Confidence وابسته نیست.
- پیش‌فرض: Narrative v0؛ Confidence رأی تاریخی غیرکالیبره است. در SWITCH مقدار Confidence موجود نیست.
- ورودی: متن اصلی Target و Context فشردهٔ تاریخی Narrative با Source Hash؛ هیچ همسایهٔ جدید، GT یا Summary جدید ساخته نمی‌شود. Context همسایه ممکن است خلاصهٔ تاریخی باشد؛ Quote معتبر فقط از Target پذیرفته می‌شود.
- خروجی: KEEP، SWITCH یا ABSTAIN؛ دادهٔ نامعتبر یا مفقود UNAVAILABLE است و به Baseline تبدیل نمی‌شود.
- SWITCH: Quote دقیق Target، کلاس معتبر متفاوت از Narrative، موضوع غیرخالی غیرمعادل نام کلاس، عدم تعارض ساختاری و uncertainty=NONE. Counter-quote حل‌نشده اجازهٔ SWITCH نمی‌دهد. Quote دقیق یا توضیح Topic، تأیید مستقل معنایی نیست؛ L2=NOT_ASSESSED.
- کنترل‌ها: Narrative کامل؛ Router-only با حذف همان ۳۷ هدف؛ Narrative روی Mask پذیرفته‌شدهٔ Lite؛ کنترل تعداد کلاس با انتخاب Hash-مرتب Narrative، در صورت ظرفیت کافی. کنترل پولی Self-consistency سازگار موجود نیست؛ اجرای آن جزو این Manifest نیست.
- معیار اصلی: Fix/Harm نسبت به کنترل Narrative روی دقیقاً همان Accepted IDs؛ معیارهای تمام Cohort و Coverage جدا هستند.
- Smoke: دو هدف اول با ترتیب Hash ثابت، جزو همان ۳۷ درخواست؛ بدون Retry و با توقف برای بازبینی پیش از Scale.

Protocol SHA: `9a2258be64b73583b1c4fd014ca7caa1aab179f90b909fc24e222244f0d7dadd`

Manifest SHA: `dea21474fc5027237f3ea8e69999eb98dd18e7ebb40e0ead18400600f2e0088a`

Selected-order SHA: `eb57ee91d4726b0cfa1983ce563656c895b2e61e94667b0fd5575b9775f56201`

## هزینه و وضعیت اجرا

Provider منتخب مالک GapGPT است؛ نام OPENAI_API_KEY به معنی مهاجرت به OpenAI نیست. Credential باید فقط در Terminal مخفی یا GAPGPT_API_KEY فرآیند وارد شود، هرگز در چت.

[تعرفهٔ رسمی GapGPT](https://gapgpt.app/platform-v2/pricing) در بررسی ۲۰۲۶-۱۱-۱۲، مدل gpt-6-luna و نرخ Input=$0.10/M، Output=$0.50/M را فهرست می‌کند. این فهرست تضمین Revision، Privacy/Retention، سازگاری لحظه‌ای یا صورتحساب نیست. دو شناسهٔ برگشتی دقیق مجاز تاریخی ثبت شده‌اند؛ نسخهٔ جدید خودکار پذیرفته نمی‌شود.

تنظیم پیشنهادی همسان اجرای اخیر: temperature=1، n=1، max_tokens=4096 و reasoning_effort حذف‌شده. Input واقعی تخمینی 42241 توکن برای ۳۷ درخواست؛ با فرض 512 Output برای هر پاسخ حدود $0.0136961. رزرو محافظه‌کارانه با Input≤32768 و Output≤4096 برای هر درخواست: $0.1970176. سقف پیشنهادی $0.25 هنوز تأیید نشده است. Reasoning در رزرو Output قرار می‌گیرد؛ Billing واقعی نامعلوم است.

آماده‌سازی آفلاین:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_sara_lite.py -v
.venv\Scripts\python.exe -B -m llmgnn_sara.annotation.sara_lite
```

چهار تست Synthetic فعلی KEEP/SWITCH/Third-class/ABSTAIN، Quote نامعتبر، تناقض، Missing، Schema و Confidence را پاس کردند. تست‌های Resume/Budget/Controls و Runner پولی هنوز تکمیل نشده‌اند؛ این فایل مجوز Dispatch نیست. بعد از تأیید بودجه و Privacy، Adapter محدود با زیرساخت موجود تکمیل و تست می‌شود، سپس Smoke محلی با ورود مخفی کلید قابل اجرا خواهد بود. هیچ Training خودکاری وجود ندارد.

Admission مستقل، مشخصات ثابت CE/WCE و کنترل Mask برای هر GCN آینده لازم است. SWITCHها Confidence معتبر تاریخی ندارند. هیچ نتیجه یا برتری Lite هنوز اثبات نشده است. LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT.
