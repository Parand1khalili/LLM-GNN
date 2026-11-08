# خلاصهٔ جامع روند پژوهش، بازیابی و توسعهٔ LLM-GNN / SARA

تاریخ نگارش: ۶ نوامبر ۲۰۲۶، منطقهٔ زمانی America/Los_Angeles. آخرین snapshot آزمایشیِ منابع: ۵ نوامبر ۲۰۲۶.

این سند برای فهم پیوستهٔ پروژه و انتقال آن به ادامهٔ کار تهیه شده است: از مبنای مقاله و آزمایش‌های قدیمی، تا ازدست‌رفتن محیط، بازیابی، بازسازی نرم‌افزار، پایلوت واقعی، داوری انسانی و آخرین batch متوقف‌شده. دستورها و مجوزهای نقل‌شده در تاریخچه، موضوع گزارش‌اند؛ این خلاصه مجوز اجرای API، آموزش، ارزیابی GT، push یا تغییر پروتکل نیست.

## ۱. تصویر فعلی در یک نگاه

پروژه اکنون یک کدبیس پایتون یکپارچه، داده‌های frozen قابل‌ردیابی، بازپخش آفلاین موفق، ابزار نمایش GraphScope و اجرای واقعیِ ثبت‌شدهٔ SARA-3 دارد. بااین‌حال، آزمایش نهایی SARA-3 کامل نشده و بهبود کیفیت برچسب یا عملکرد GCN به‌وسیلهٔ Agent سوم هنوز اثبات نشده است.

| موضوع | آخرین وضعیت ثبت‌شده |
|---|---|
| مخزن محلی | `C:\Users\Admin\Documents\ChatGPT\llm-gnn`، شاخهٔ `main` |
| HEAD، بررسی‌شده در زمان نگارش | `2373b9685b195080d81f3fcecd88001a9b04a8ff` |
| B1 و Narrative v0 | ۲۸۰/۲۸۰ رأی از parsed sampleهای تاریخی با frozen outputs برابر شده‌اند |
| پاسخ‌های خام تاریخی | admission کامل ۸۴۰ raw response هنوز احراز نشده است |
| گراف کامل Cora | topology بازیابی شده؛ این به معنی بازتولید features یا training نیست |
| Routerها | R0، Semantic-v0، R1-v1، R1-v2 و R2-v1 موجود؛ برتری علمی آن‌ها مشخص نیست |
| پایلوت legacy | شش blind با پاسخ HTTP200 و دو comparison؛ paired protocol ناتمام |
| بررسی انسانی خروجی واقعی | شش پاسخ برای سه پرونده، با استقلال خوداظهاری‌شده |
| batch واقعی Rich V2/512 | یک درخواست؛ رد به‌علت truncation |
| batch واقعی Rich V2/4096 | ۵۳ درخواست؛ ۵۲ COMPLETED، یک REJECTED، صفر UNCERTAIN |
| محل توقف batch اخیر | گرهٔ ۱۸۱۴، فاز compare، `L1_DUPLICATE_EVIDENCE` |
| خروجی اخیر Agent سوم | `provisional_count=0`؛ صفر برچسب آموزشی جدید از routed verification |
| ۹۳ برچسب حفظ‌شده | baselineهای بدون review؛ تأیید Agent سوم محسوب نمی‌شوند |
| L2 در runtime فعلی | `NOT_ASSESSED`؛ Automated Concordance تأیید معنایی مستقل نیست |
| GT evaluation و GCN جدید SARA-3 | انجام‌شدن آن‌ها در شواهد نهایی احراز نشده است |
| آخرین regression محلی گزارش‌شده | ۴۲۲ تست: ۴۱۸ PASS، یک FAIL، یک ERROR، دو SKIP |
| GitHub و Drive | سابقهٔ push وجود دارد؛ backup فعلی مستقلاً در این نوبت بررسی شبکه‌ای نشده؛ backup جدید Drive تأیید نشده است |

اعداد آزمایشی و تست‌های این جدول از منابع خوانده‌شده نقل شده‌اند؛ در نوبت نگارش این خلاصه، آزمایش یا regression پروژه دوباره اجرا نشده است.

## ۲. منابع و شیوهٔ تفسیر آن‌ها

دو منبع اصلی:

1. `C:\Users\Admin\Desktop\PROJECT_HANDOFF_2026-11-05_FA.md`؛ ۸۰٬۴۵۵ بایت. سند انتقال متأخر با ۲۸ بخش و سه پیوست؛ آخرین وضعیت، یافته‌های ممیزی، commitها، آمار batch و محدودیت‌ها را جمع می‌کند.
2. `C:\Users\Admin\Desktop\خلاصه بازیابی.txt`؛ ۱٬۱۳۴٬۲۵۰ بایت. تاریخچهٔ بلند گفتگو، briefهای اجرایی، خروجی ترمینال، اصلاح نظرها، نتایج و دستورهای پیشنهادی از بازیابی تا batch واقعی.

منابع کمکی محلی: `PROJECT_STATE.md`، `AGENTS.md`، وضعیت و تاریخچهٔ Git و بخش آغازین `reports/PROJECT_HANDOFF_AUDIT_2026-11-05.json`. این بررسی جای ممیزی مجدد کل کد یا رسیدهای خصوصی نیست.

فایل متنی، یک گزارش یکدست با یک تاریخ قطع نیست. جمله‌هایی مثل «R2 نداریم»، «API اجرا نشده»، «remote نداریم» یا «L2 انسانی صفر است» به زمان خودشان مربوط‌اند و در ادامهٔ همان تاریخچه تغییر می‌کنند. سند انتقال ۵ نوامبر نیز snapshot است؛ نباید آن را بدون بررسی رخدادهای بعدی وضعیت همیشگی پروژه دانست.

سطوح منشأ باید جدا بمانند:

| برچسب | معنی |
|---|---|
| `RECOVERED_EXACT` | اصل بایت‌های artifact با شاهد معتبر تطبیق داده شده است |
| `RECONSTRUCTED` | پیاده‌سازی یا قرارداد از شواهد و specification دوباره ساخته شده است |
| `REPRODUCED` | محاسبه‌ای با اجرای ثبت‌شده دوباره تولید شده است؛ دامنهٔ آن باید مشخص باشد |
| `HISTORICAL_REPORTED` | نتیجهٔ تاریخیِ نقل‌شده؛ معادل اجرای تازه نیست |
| `UNVERIFIED` / `MISSING_EVIDENCE` | هویت، جزئیات، دسترسی یا ادعا هنوز اثبات نشده است |

داشتن hash در گزارش، به‌تنهایی به معنی داشتن فایل اصلی، بررسی آن فایل یا بازاجرای موفق آن نیست.

## ۳. سؤال علمی و ارتباط با مقاله و پروپوزال

مرجع پژوهش، مقالهٔ Chen و همکاران با عنوان *Label-Free Node Classification on Graphs with Large Language Models (LLMs)*، ICLR 2024 است. خط اصلی چنین است:

`Graph / Text → Active Node Selection → LLM Annotation + Confidence → Optional Post-filtering → GCN Training → Isolated Evaluation`

پروژه می‌پرسد آیا افزودن context واقعی گراف به annotation و سپس بررسی مستند موارد مشکوک، pseudo-labelهای مفیدتری تولید می‌کند و آیا این تغییر، در برابر هزینه‌اش، عملکرد downstream GCN را بهتر می‌کند.

چهار تفکیک روش‌شناختی ضروری است:

- **B1** یک baseline محلی متن‌محور و الهام‌گرفته از مقاله است؛ بازتولید دقیق B0، مدل یا cache رسمی مقاله نیست.
- **Narrative v0** متن همان target را با شواهد واقعی همسایگی یک‌جهشی ترکیب می‌کند. B1 و v0 دو prompting arm برای **همان LLM پایه** هستند؛ دو مدل مستقل نیستند.
- **FeatProp** انتخاب target در مطالعهٔ frozen بوده است؛ برابر C-Density مطرح‌شده در پروپوزال نیست. انتخاب target با FeatProp و انتخاب context با شباهت SBERT نیز دو عملیات متفاوت‌اند.
- **Uniform2Path3** نمونه‌گیری deterministic از مسیرهای واقعی دوگامی است؛ random walk واقعی نیست. تمام variantهای پیشنهادی پروپوزال اجرا نشده‌اند.

SARA-2 و SARA-3 توسعه‌های پژوهش حاضر روی زنجیرهٔ مقاله‌اند. در مقاله، برخی promptهای ساختاری ساده نتیجهٔ بدتری داشته‌اند؛ بنابراین برتری ساختار در prompt را نمی‌توان مفروض گرفت. نتیجهٔ مثبت محلی Narrative نیز نتیجهٔ خود مقاله نیست.

معیار نهایی downstream GCN است. دقت خام annotation، پشتیبانی معنایی، coverage، حفظ کلاس‌ها، abstention و هزینه معیارهای مکمل‌اند. بالا رفتن selective accuracy همراه با حذف تعداد زیادی target ممکن است به training آسیب بزند.

## ۴. آزمایش‌های پیش از FeatProp؛ دستاوردها و محدودیت‌ها

این بخش سابقهٔ تاریخی است و در نگارش حاضر بازاجرا نشده است. مطالعه‌های PageRank2، CiteSeer، دوگامی و FeatProp را نباید در یک جدول matched واحد ادغام کرد.

### M1: Cora / PageRank2 / همسایگی یک‌جهشی

| روش | GCN بدون PS (%) | GCN با PS (%) |
|---|---:|---:|
| B1 | 68.13 | 71.05 |
| Raw3 | 67.94 | 70.43 |
| Rep1 | 67.87 | 70.69 |
| 1-hop Consensus | 69.50 | 70.90 |

Consensus در noPS بهتر بود، اما با PS از B1 بالاتر نبود. raw تاریخی این فاز برای B1 برابر ۹۴/۱۴۰ و Consensus برابر ۹۵/۱۴۰ گزارش شده؛ با rawهای مطالعهٔ پنج prompt یا FeatProp یکی نیست.

### M2: Agreement تاریخی Cora

Agreement+PS برابر ۶۹٫۵۷٪، Agreement-only با ۱۲۷ target و noPS برابر ۷۰٫۲۸٪ و Agreement+WCE برابر ۷۰٫۰۲٪ گزارش شده است. این توسعه post-hoc بود و با Agreement-only متأخرِ FeatProp فرق دارد.

### M3: CiteSeer

GCN گزارش‌شده: B1 برابر ۶۴٫۸۱۸٪، Consensus برابر ۶۴٫۱۲۳٪ و Agreement-only برابر ۶۴٫۹۲۷٪. سود Agreement نسبت به B1 فقط ۰٫۱۰۹ نقطهٔ درصد بود.

در نسخه‌های raw و fixedِ CiteSeer اختلاف graph/features/labels ثبت شده بود؛ در تاریخچه ۱۳۴ اختلاف label از ۳۱۸۶ گره گزارش شده است. استفادهٔ historical از `fixed_y` مربوط به evaluator بود؛ این labelها ورودی annotation یا routing نیستند. این خلاصه GT را باز یا decode نکرده است.

### M4-A-R1: مسیرهای واقعی دوگامی

H2Path3 مسیرها را با شباهت معنایی رتبه‌بندی می‌کرد؛ Uniform2Path3 از همان فضای نامزدها deterministic و بدون جایگذاری انتخاب می‌کرد. تعداد response slotهای این مطالعه ۱۵۶۰ و GCN fitها ۴۰ بود؛ وقفهٔ quota در CiteSeer Uniform و ادامهٔ کنترل‌شده نیز در سابقه ثبت شده است.

| Dataset | raw صحیح H2 | raw صحیح Uniform | H2 GCN mean ± SD (%) | Uniform GCN mean ± SD (%) |
|---|---:|---:|---:|---:|
| Cora | 95/140 | 95/140 | 68.9836 ± 0.1682 | 69.4237 ± 0.2029 |
| CiteSeer | 89/120 | 91/120 | 61.7221 ± 0.4532 | 64.0150 ± 0.3301 |

مقایسهٔ H2/Uniform درون همین مطالعه matched بود، اما comparator هم‌شرط B1 در ۴۰ fit اولیه اجرا نشده بود. اجرای ۲۰ fit تکمیلی B1 پیشنهاد شده، ولی نتیجهٔ آن در این دو منبع احراز نشده است.

**اختلاف ثبت نام معیار:** مقادیر ۰٫۱۸۵۱۷۵، ۰٫۱۸۱۳۸۳، ۰٫۰۸۳۷۷۸ و ۰٫۰۷۸۸۵۱ در متن تاریخی با عنوان ECE و در پیوست handoff با عنوان Brier آمده‌اند. بدون مراجعه به artifact و تعریف محاسبه، نباید یکی از این دو نام را قطعی کرد.

### مطالعهٔ پنج prompt روی PageRank2

بودجهٔ تاریخی: ۱۴۰ target × پنج arm × سه sample، یعنی ۲۱۰۰ slot. raw صحیح: B1=89، Consensus=91، Narrative v0=96، v1=92 و v2=91 از ۱۴۰. GCNهای گزارش‌شدهٔ noPS:

| روش | GCN mean ± SD (%) |
|---|---:|
| B1 | 64.96495 ± 0.45146 |
| Narrative v0 | 70.63084 ± 0.20443 |
| Narrative v1 | 69.17445 ± 0.25128 |

در runner قدیمی، باقی‌ماندن حالت eval پس از epoch اول گزارش شده است. این اعداد باید با رفتار frozen همان کد معرفی شوند، نه با training اصلاح‌شده یکسان تلقی شوند. اشتراک targetهای این مطالعه با FeatProp فقط ۱۴ گره بوده است.

## ۵. مطالعهٔ اصلی matched FeatProp؛ پایهٔ علمی حفظ‌شده

دادهٔ اصلی Cora با ۲۷۰۸ گره، هفت کلاس و ویژگی SBERT گزارش‌شده با ابعاد ۲۷۰۸×۳۸۴ است. ۱۴۰ target با FeatProp انتخاب شد. Primary شامل ۱۳۵ complete-case و Sensitivity شامل کل ۱۴۰ target است؛ test مشترک، مکمل **تمام ۱۴۰ target** و برابر ۲۵۶۸ گره است.

پنج target تکمیل‌شده با پاسخ supplementary عبارت‌اند از `711,979,1716,2270,2291`. حذف آن‌ها از Primary به معنی انتقالشان به test نیست.

تنظیم annotation تاریخی: `gpt-6-luna`، دمای ۰٫۷، `n=1` و سه درخواست مستقل برای هر node/arm؛ ساختار اصلی، wrapper و voter بین دو arm کنترل شده بود. Narrative شواهد محلی را با تقدم متن target اضافه می‌کرد. reasoning صریح و `max_tokens` در ساخت درخواست matched تاریخی مشاهده نشده‌اند؛ حذف reasoning parameter به معنی خاموش‌بودن reasoning نیست.

| Cohort | B1 raw صحیح | Narrative v0 raw صحیح |
|---|---:|---:|
| Primary | 92/135 = 68.148148% | 97/135 = 71.851852% |
| Sensitivity | 96/140 = 68.571429% | 101/140 = 72.142857% |

این دقت‌ها تاریخی‌اند؛ برای این خلاصه GT دوباره بررسی نشده است. برچسب‌ها پیش از raw GT evaluation منجمد شدند، ولی قرارداد GCN پس از مشاهدهٔ raw accuracy نهایی شده بود؛ کل مطالعه نباید کاملاً preregistered پیش از هر outcome نامیده شود.

### ۱۶۰ fit اصلی GCN

طرح: دو cohort × چهار ترکیب loss/PS × دو arm × ده seed. جدول زیر historical است و خروجی training جدید محسوب نمی‌شود. SD از نوع population با `ddof=0` روی seedهای training است.

| Cohort / Loss / PS | train هر arm | B1 mean ± SD (%) | v0 mean ± SD (%) | paired Δ mean ± SD (pp) |
|---|---:|---:|---:|---:|
| Primary / CE / noPS | 135 | 69.680685 ± 0.411816 | 70.954050 ± 0.412644 | +1.273364 ± 0.368212 |
| Primary / WCE / noPS | 135 | 70.486760 ± 0.322739 | 72.671340 ± 0.528448 | +2.184579 ± 0.380526 |
| Primary / CE / PS | 95 | 70.735981 ± 0.543849 | 71.911994 ± 0.432944 | +1.176012 ± 0.510348 |
| Primary / WCE / PS | 95 | 70.097352 ± 0.597573 | 72.017134 ± 0.609570 | +1.919782 ± 0.688504 |
| Sensitivity / CE / noPS | 140 | 69.844237 ± 0.404385 | 71.732866 ± 0.458593 | +1.888629 ± 0.455208 |
| Sensitivity / WCE / noPS | 140 | 70.595794 ± 0.344555 | 73.165888 ± 0.448564 | +2.570093 ± 0.273141 |
| Sensitivity / CE / PS | 98 | 71.024143 ± 0.310771 | 71.974299 ± 0.323021 | +0.950156 ± 0.203240 |
| Sensitivity / WCE / PS | 98 | 71.460280 ± 0.403352 | 72.305296 ± 0.482866 | +0.845016 ± 0.334098 |

طبق گزارش تاریخی، v0 در هر هشت condition و تمام ۸۰ اختلاف seed-level بالاتر بود. این ۸۰ اختلاف، ۸۰ annotation مستقل نیست. قوی‌ترین نتیجهٔ محلی جدول، Sensitivity/WCE/noPS با +۲٫۵۷۰۰۹۳pp است؛ سهم جداگانهٔ هر جزء prompt بدون ablation مشخص نشده است.

اعداد مقاله، از جمله Cora/PS-FeatProp-W برابر ۷۶٫۲۳±۰٫۰۷٪، comparator منتشرشده‌اند. مقایسهٔ مستقیم این عدد با ۷۳٫۱۶۵۸۸۸٪ محلی، به‌علت تفاوت setting، مدل و پروتکل head-to-head محسوب نمی‌شود.

### ۲۰ fit جداگانهٔ Agreement-only FeatProp

دو arm در Primary روی ۱۲۶/۱۳۵ و در Sensitivity روی ۱۳۱/۱۴۰ موافق بودند. Agreement-only نه اختلاف را از training حذف می‌کرد، بدون تغییر test.

| Cohort | retained | GCN mean ± SD (%) | Δ نسبت به B1 CE/noPS | Δ نسبت به v0 CE/noPS |
|---|---:|---:|---:|---:|
| Primary | 126 | 71.211059 ± 0.446395 | +1.530374pp | +0.257009pp |
| Sensitivity | 131 | 71.569315 ± 0.428862 | +1.725078pp | −0.163551pp |

توافق به‌تنهایی همیشه بهترین فیلتر downstream نبود. مجموع ۱۶۰+۲۰ برابر ۱۸۰ fit است و M1–M4 را شامل نمی‌شود.

## ۶. چرا SARA-2 و سپس SARA-3 مطرح شدند؟

SARA-2 با Policy 002 برای استفاده از agreement/confidence و ارجاع موارد مشکوک طراحی شد. در سابقهٔ Sensitivity، R0 تعداد ۳۷/۱۴۰ target را ارجاع می‌داد: نه disagreement و ۲۸ توافق کم‌اطمینان‌تر؛ صفر HH. ۱۰۳ گره direct می‌ماندند.

E0 پس از freeze و با GT تشخیصی نشان داد: هر دو صحیح=۹۵، فقط B1 صحیح=۱، فقط v0 صحیح=۶ و هر دو غلط=۳۸. از ۳۸ خطای مشترک، ۳۶ مورد کلاس غلط یکسان داشتند. در ۹۳ توافق HH، ۷۲ هر دو صحیح و ۲۱ هر دو غلط بودند. R0 از ۴۵ گرهٔ دارای حداقل یک خطا ۲۱ را ارجاع داده و ۲۴ را از قلم انداخته بود.

E1 نیز exploratory باقی ماند؛ نشانه‌های post-hoc برای تعیین علت تمام خطاها یا تثبیت router معتبر کافی نبودند. این یافته‌ها انگیزهٔ پژوهش‌اند؛ جدول خطاها، GT و correctness نباید وارد runtime، Atlas، انتخاب گره، prompt یا threshold tuning شوند.

محدودیت بنیادی V1: اگر B1 و v0 هر دو کلاس غلط یکسان بدهند، انتخاب میان همان دو کلاس نمی‌تواند کلاس صحیح جدیدی ایجاد کند. V1 ممکن است آن مورد را حذف/abstain کند؛ اصلاح با کلاس سوم، آزمایش مستقلی با مجوز و پروتکل جداست.

SARA-3 برای بررسی این مسئله، Atlas عمومی، routing آگاه از محتوا، blind-first verifier، شواهد قابل‌ممیزی و arbitration محافظه‌کار را اضافه کرد. کیفیت و منفعت این ترکیب هنوز باید با آزمایش مستقل و downstream سنجیده شود.

## ۷. ازدست‌رفتن محیط و بازیابی واقعی

workspace دوران Codex در `D:\SARA2` از دست رفت. کد، tests و ledgers مربوط به SARA-2، E0/E1، SARA-3 و P0/P1/P2 آن محیط recovered executable نیستند. گزارش‌های آن دوره specification و سابقهٔ پژوهش‌اند؛ P2 فقط آخرین checkpoint گزارش‌شده بود.

پایهٔ recovery، آرشیو pre-Codex در [Prnd-project](https://drive.google.com/drive/folders/1u9eLA8uZVJxZsLi38h1-eDPhNDwj92ML) و [notebook اصلی Colab](https://colab.research.google.com/drive/1VTFrVkixOMmnkXEGWprtE7m4rSWuqJsY) است. مشکل حساب/shared access یا نتیجه‌ندادن جست‌وجوی connector، اثبات حذف فایل نیست.

شواهد recovery شامل sourceهای اصلی، frozen predictions، selection، promptها، نتایج/receiptهای تاریخی و weight artifactها بود. گزارش قدیمی از ۱۸۰ weight و notebook با ۵۶۸ سلول، شامل ۵۴۵ سلول کد، سخن می‌گوید؛ این خلاصه آن‌ها را مجدداً byte-audit نکرده است.

۲۵ snapshot منتخب در `recovered_sources/` و manifest مربوط حفظ شدند. شمارش اصلاح‌شدهٔ archive در handoff: ۴۳ فایل داخل src، شامل ۲۵ مشابه upstream، شش modified و ۱۲ added؛ `startup.py` بیرون src سیزدهمین addition پژوهشی است. این عدد با ۲۵ snapshot منتخب متفاوت است.

upstream برابر `CurryTang/LLMGNN@1f60eedb1452cdd997be18b5dd932a02666ee57e` بود؛ آن مخزن مقصد backup پژوهش شخصی نیست. `startup.py`، scriptهای تاریخی دارای side effect و pickleهای نامطمئن نباید کورکورانه اجرا شوند.

### شکاف raw response

۸۴۰ reference از ۷۲۶ fresh، ۳۰ supplementary و ۸۴ reused تشکیل می‌شود. گزارش‌های پیشین readback بخشی از rawها را ذکر می‌کنند، اما ممیزی handoffِ ۵ نوامبر صفر raw تاریخی از این مجموعه را مستقلاً hash-admit کرده بود. ۴۸ reuse هنوز unresolved access است؛ نه proven missing.

`missing_raw_count=840` در intake قدیمی فقط به معنی نرسیدن bytes به همان intake است. هیچ raw گمشده‌ای نباید با parsed answer، برچسب frozen یا خروجی ساختگی جایگزین شود.

ابزار Colab recovery و ZIP admission آماده شد: `scripts/colab_recover_responses.py` و `scripts/verify_intake.py`. این‌ها برای یافتن و بررسی raw اصلی، کنترل hash/CRC و جلوگیری از conflict/traversal هستند. تکمیل ZIP admitشده در آخرین شواهد احراز نشده است.

تصمیم مهم مالک در ۳۰ اکتبر: recovery کامل ۸۴۰ raw دیگر شرط آغاز **offline implementation و parsed replay** نباشد؛ شرط raw parsing و ادعای byte-level reproducibility همچنان باقی بماند.

## ۸. بازسازی کدبیس واحد و milestones آفلاین

به‌جای ساخت پروژه از صفر یا درخت‌های v001 متعدد، روی مخزن موجود و شاخهٔ main یک package نصب‌پذیر در `src/llmgnn_sara/` ساخته شد. بخش‌های اصلی عبارت‌اند از io، selection، annotation، filtering، sara2، sara3، pilot، downstream و evaluation مجزا.

ترتیب تحقق milestones:

1. package، CLI، configuration، admission ورودی‌ها و مسیر وابستگی‌ها ساخته شد.
2. voter دو arm از sampleهای parsed بازسازی شد؛ هر ۲۸۰ خروجی، کلاس، confidence و fallback با frozen تطبیق یافت.
3. PS و class guard در چهار cohort–arm با ترتیب retained/deleted تطبیق داده شد.
4. SARA آفلاین، blind-first، arbitration، abstention و ممنوعیت کلاس سوم با fixture تست شد.
5. planهای matched GCN و forward مصنوعی چهارگرهی آماده و تست شدند؛ training واقعی اجرا نشد.
6. ۹ JSON hash-pinned، متن واقعی هر ۱۴۰ target و neighborhood ثبت‌شده را به pipeline متصل کردند؛ ۲۸۰ prompt با ۸۴۰ reference تطبیق یافت.
7. pilot شش‌گرهی و sealهای آن آماده شد؛ checkout تمیز و اجرای tokenizer نیز بررسی شدند.

جزئیات voter مهم است: denominator شامل invalid sampleها، tie با اولین occurrence، confidence طبق loop تاریخی و all-invalid fallback مبتنی بر آخرین sample/edit distance و نصف‌شدن confidence است. replayِ همین رفتار با بازتولید raw parser یا ارسال دوبارهٔ annotation تفاوت دارد.

برای PS، حذف sequential، tie با global node ID، حفظ آخرین عضو کلاس و ترتیب manifest مهم‌اند. frozen FeatProp replay نیز ادعای reselection دقیق تحت float64 در برابر Torch float32 تاریخی نیست.

milestone اولیه ۹۲ تست با ۹۱ PASS و یک SKIP داشت؛ authentic pilot به ۱۰۲ تست با ۱۰۱ PASS و یک SKIP رسید. این‌ها نتایج همان checkpoints هستند، نه آخرین regression پروژه.

## ۹. GraphScope؛ مسیر موازی نمایش و بازیابی topology

کاربر یک UI علمی، مینیمال و تعاملی می‌خواست که مانند مقالهٔ قابل‌کاوش باشد: انتخاب گره، نمایش همسایه، مقایسهٔ annotation و پیگیری مراحل پژوهش. این کار هنگام محدودیت مصرف Codex به مسیر موازی frontend تبدیل شد؛ قرار نبود شرط پیشرفت علمی باشد.

GraphScope v2 در `web/graphscope/` با React، TypeScript، Vite و Cytoscape ساخته شد. شش بخش آن Overview، Explore، Workflow، Methods، Experiments و Prediction Desk هستند. تعامل‌های اصلی شامل search، pan/zoom، hover همسایه‌ها، inspector همگام، selection در URL، نمودار seedها و fallback فهرست گره‌هاست.

export پژوهشی: ۴۷۸ node، ۵۲۵ edge ثبت‌شده، ۲۸۰ annotation و ۱۶۰ fit تاریخی. این partial research evidence با full graph فرق دارد. نمای قدیمی PageRank2 با ۴۶۰ node و ۴۶۷ edge نیز cohort دیگری بود.

بعداً توپولوژی کامل از فایل اصلی `cora_random_sbert.pt` بازیابی شد؛ SHA-256:

`9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`

روش گزارش‌شده ZIP و `pickletools` metadata inspection بود؛ نه `torch.load`، unpickle یا اجرای pickle VM. فقط edge storage خوانده شد، بدون decode برچسب‌ها.

نتیجه: ۲۷۰۸ node، ۱۰۸۵۸ directed entry، ۱۰۵۵۶ unique directed، ۳۰۲ repeated directed، ۵۲۷۸ unique undirected، صفر self-loop و isolated. متن/degree هر ۱۴۰ target و وجود تمام ۵۲۵ research edge تطبیق یافت. این موفقیت مربوط به topology است، نه admission کامل feature matrix یا training.

سایت static است؛ inference و training اجرا نمی‌کند. وجود workflow و build آماده، اثبات انتشار GitHub Pages نیست. عمومی‌شدن محتوای سایت با خصوصی‌بودن repo یکی نیست؛ دادهٔ خصوصی مدل/داور نباید به export اضافه شود. وضعیت «verifier اجرا نشده» در export قدیمی فقط مربوط به همان snapshot است.

## ۱۰. P0/P1/P2 تاریخی با پایلوت جدید فرق داشتند

| موضوع | P0 تاریخی | feasibility جدید |
|---|---|---|
| گره‌ها | هشت node ثابت | شش node ثابت |
| طراحی | Judge002 و SARA3_V1 روی گروه A؛ V1 تنها روی گروه B | blind و comparison مشروط |
| معنای ۱۲ | دوازده رکورد منطقی `(node, arm)` | حداکثر دوازده stage intent |
| provider پیشنهادی | Direct OpenAI / Responses | GapAPI و سپس GapGPT / Chat Completions |
| وضعیت equivalence | wire/schema/Policy کامل مفقود | پیاده‌سازی جدید و صریحاً متمایز |

P0 تاریخی: گروه A=`734,2379,2490,682`، هرکدام Judge002 و V1؛ گروه B=`1031,655,1013,1328`، فقط V1. یعنی هشت node و ۱۲ logical record، نه الزاماً ۱۲ generation. فرض دو call برای هر V1 می‌تواند بودجه را تغییر دهد و تاریخی بودنش ثابت نشده است.

P1 قدیمی ۱۲ logical wire با مجموع گزارش‌شدهٔ ۱۱۵۸۷۳ بایت، fake transport و ledger آفلاین داشت. P2 بررسی readiness و کنترل‌های گزارش‌شده بود؛ نه generation واقعی. سورس و bytes اصلی آن‌ها recovered نیستند.

manifest هشت‌گرهی و validator تازه ساخته و قراردادهای missing مستند شدند. عضویت گروه B در R1 تاریخی همچنان گزارش‌شده/تأییدنشده است. تصمیم بعدی این بود که missing detailها مانع دائمی توسعه نشوند: baseline و اصل تصمیم‌های علمی حفظ شوند و طراحی تازه نام و نسخهٔ صریح داشته باشد.

## ۱۱. L1، شواهد غنی، L2 و حفاظت از برچسب آموزشی

### L1: کنترل قطعی ساختار و منشأ

L1 با Python schema، class ID، abstention، source/hash/reference و نقل‌قول را بررسی می‌کند. پاسخ متناقض silently repair نمی‌شود. raw response پیش از comparison در audit خصوصی و content-addressed ثبت می‌شود؛ شکست audit نیز fail closed است.

در قرارداد فعلی، quote باید از `target.text` باشد؛ وجود neighbor در prompt مجوز جا زدن متن neighbor به‌عنوان quote هدف نیست. case، فاصله و punctuation مهم‌اند. حدهای گزارش‌شده شامل حداکثر چهار evidence item، quote حداکثر ۵۱۲ character و حداقل غیر trivial بودن است.

duplicate quote، حتی بین support و counter، فعلاً رد می‌شود. L1 فقط provenance را می‌سنجد؛ quote واقعی اما نامرتبط می‌تواند L1 PASS بگیرد.

### Rich Evidence و Rich Prompt V2

schema نسخهٔ `sara.verifier.rich_evidence.v1` شامل `primary_topic`، supporting/counter evidence با `source_id/quote/claim`، `auxiliary_method_warning` و `uncertainty_reason` است. کامل‌بودن این فیلدها یا معتبر بودن quote حقیقت claim را ثابت نمی‌کند.

بعداً در builder غنی، ازبین‌رفتن دستور خاص comparison زیر دستورهای عمومی شناسایی شد. prompt opt-in نسخهٔ `sara.verifier.rich_prompt.v2` blind/comparison را روشن‌تر جدا کرد و exact بودن **EVERY** quote، با حفظ case/space/punctuation و بدون wrapper تزئینی را خواست. promptها و sealهای legacy بازنویسی نشدند.

### L2: معنای شواهد

rubric رسمی چهار بُعد دارد: ارتباط با موضوع اصلی، پشتیبانی quote از claim، رسیدگی به counter-evidence مهم و تفکیک روش جانبی از موضوع پژوهش. outcomeها SUPPORTED، UNSUPPORTED، AMBIGUOUS و NOT_ASSESSED هستند.

شش case توسعه‌ای illustrative برای quote مرتبط، copyright نامرتبط، خلط روش جانبی، تعارض، ابهام Bayesian/neural و نبود ورودی قابل‌ارزیابی ساخته شد. این‌ها gold یا holdout مستقل نبودند.

workflow رسمی `sara.l2.human_review.v1` برای packet کور، دو reviewer، چهار dimension، rationale، evidence refs و timestamp ساخته شد. Shadow نسخهٔ `sara.l2.shadow.v1` فقط assessmentهای supplied را با حالت‌های NOT_ASSESSED/ASSESSED/INVALID/UNAVAILABLE ثبت و مقایسه می‌کند؛ خودش judge نیست و ASSESSED مجوز training نیست.

در ادامه، مالک خواست اجرای اصلی به human approval برای هر node وابسته نباشد. این تصمیم باعث ساخت مسیر خودکار آزمایشی شد؛ اما اعتبارسنجی معنایی مستقل با یک قاعدهٔ سازگاری جایگزین و «اثبات‌شده» اعلام نشد.

## ۱۲. بازطراحی مستند Routerها؛ حفظ baseline و رفع missing coverage

تمام candidateها GT-free و deterministic طراحی شدند. Atlas موجود هفت تعریف عمومی و چهار keyword برای هر کلاس، مجموع ۲۸ keyword دارد؛ ابزار lexical محدود است، نه entailment یا semantic judge.

R0 فعلی با امتیاز `100*disagreement + 100 - min(confidences)` رتبه می‌دهد؛ tie با node ID صعودی. threshold retention توافق بدون review برابر ۸۰، بازسازی‌شده و کالیبره‌نشده است؛ Policy002 کامل تاریخی محسوب نمی‌شود.

Semantic-v0 از R0 و lexical mismatch استفاده می‌کند؛ نام «semantic» نباید به‌عنوان فهم معنایی اثبات‌شده تفسیر شود.

R1-v1 سه جزء داشت: disagreement به نام D، mismatch نامزدها با keywordها به نام M و ambiguity میان کلاس‌ها به نام A؛ `Risk=(D+M+A)/3`. با صفر match، M=A=1 می‌شد؛ بنابراین تمام ۳۰ مقالهٔ بدون match انتخاب شدند. ایراد مفهومی این بود که نبود اطلاعات، شاهد مثبت خطا محسوب می‌شد.

سه سیاست مقایسه شد: v1، imputation خنثی و R1-v2. v2 ریسک مشاهده‌شده را از coverage جدا کرد: `Risk=(D+I[m>0]*(M+A))/3`، coverage=`m/4` و ترتیب risk نزولی، coverage نزولی، ID صعودی. این انتخاب ممکن است unknownها را کم‌ارجاع دهد؛ صفر match به معنی امن‌بودن نیست.

R2-v1 برای توازن این نگرانی ساخته شد: چهار unknown exploration با hash ثابت، ۱۷ مورد observed risk مطابق R1-v2 و ۱۶ مورد candidate risk مطابق R0؛ overlap skip و backfill قطعی. hash exploration نمونه‌گیری تصادفی آماری نیست.

| Router؛ بودجهٔ هرکدام ۳۷ | disagreement | HH agreement | Atlas unknown |
|---|---:|---:|---:|
| R0 فعلی | 9 | 0 | 11 |
| Semantic-v0 | 9 | 11 | 6 |
| R1-v1 | 7 | 15 | 30 |
| R1-v2 | 6 | 20 | 0 |
| R2-v1 | 9 | 9 | 10 |

HH این جدول یعنی توافق با confidence هر دو حداقل ۸۰؛ وضعیت توصیفی است، نه correctness. counts تاریخی R1=۱۸ HH/۴ disagreement و R2=۷ HH/۹ disagreement مشخصات الگوریتم کامل نیستند؛ برای تطبیق این اعداد retuning انجام نمی‌دهیم.

robustness نشان داد تغییر quotaهای prespecified در R2، ۳۶/۳۷ selection را حفظ می‌کند؛ تغییر seed در order اصلی ۳۳ تا ۳۴/۳۷، اما grid ترتیب/seed فقط ۲۵ تا ۳۷/۳۷ overlap دارد. stage order بخشی از الگوریتم است. در R1-v2 نیز tie policy اثر قابل‌توجه داشت. هیچ winner از این compositionها تعیین نشد.

manifest آزمایش، R0 را control و R1-v2/R2-v1 را candidate، با دو ablation اختیاری ثبت کرد. سقف سه arm مستقل ۲۲۲ call و unionِ ۶۲ node با فرض reuse معتبر، حداکثر ۱۲۴ call بود. اجرای synthetic، ۲۰۳ logical request، ۱۱۴ fixture dispatch و ۸۹ cache hit داشت؛ این صرفه‌جویی measured API نبود.

dedup فقط با کل payload، context و dependency برابر مجاز است؛ برای comparison، class یکسان کافی نیست و hash کامل blind response نیز باید یکسان باشد. synthetic receipt پاسخ واقعی provider نیست.

## ۱۳. پایلوت واقعی legacy؛ زنجیرهٔ خطاها و اصلاحات

شش node ثابت: `637,1243,130,682,2396,653`. هدف feasibility فنی و قابلیت بررسی شواهد بود؛ نه accuracy کل یا GCN improvement.

زیرساخت ledger، intent را پیش از dispatch پایدار می‌کند؛ وضعیت uncertain پیش از امکان ارسال ثبت می‌شود تا crash سبب retry خودکار نشود. این روش تضمین exactly-once یا سقف صورتحساب نیست. درخواست‌های terminal و رسیدهای اصلی immutable باقی می‌مانند.

روند واقعی:

1. گرهٔ ۶۳۷ در endpoint قدیمی `api.gapapi.com` با HTTP401 و `invalid_api_key` رد شد. علت ریشه‌ای صرفاً از این پاسخ ثابت نمی‌شد؛ اشتباه کاربر یا کمبود اعتبار اثبات نشد.
2. تلاش مجاز و جدا روی endpoint پنل `api.gapgpt.app` با HTTP400 نشان داد `temperature=0.7` فعلاً پذیرفته نمی‌شود و default 1 لازم است.
3. wire variant صریح با temperature1 ساخته شد؛ پیام علمی sealed حفظ شد. HTTP200 و abstain دریافت شد، ولی پذیرش client به هویت مدل گیر کرد. دلیل اصلی ثبت‌شدهٔ ۶۳۷ `INVALID_ENVELOPE_OR_USAGE` است؛ نباید آن را پسینی به reason خاص‌تری بازنویسی کرد.
4. revision برگشتی `gpt-6-luna-2026-09-22` بود؛ سیاست‌های identity بعداً فقط همین revision را پذیرفته و alias درخواستی را ناخواسته حذف کردند. پس از توقف ۱۳۰، allowlist نسخه‌دار دقیق دو رشتهٔ alias و revision با تأیید مالک اصلاح شد؛ equivalence upstream اثبات نشده است.
5. blindِ ۱۲۴۳ به wrapper گیومه گیر کرد. amendment محدود `sara.l1.decorative_quote_match.v1` یک outer pair متوازن را فقط برای matching حذف کرد؛ raw و REJECTED اصلی حفظ شدند.
6. comparisonهای ۱۲۴۳ و ۱۳۰ واقعاً L1 FAIL شدند. بررسی مستقل raw/parser/source برای ۱۲۴۳ دو quote غیرعینی و برای ۱۳۰ یک quote صحیح و یک اختلاف case حرف اول یافت. باگ parser یا source mismatch در مسیر بررسی‌شده پیدا نشد؛ این نتیجه تضمین تمام کد نیست.
7. ambiguity «at least one exact quote» در prompt در برابر «every quote exact» در validator مشخص شد. برای نجات نتایج، case-insensitive/fuzzy matching فعال نشد.
8. پس از amendment صریح، سه node پایانی فقط blind شدند؛ بدون comparison. بنابراین پوشش blind کامل شد، ولی paired protocol اصلی کامل نشد.

| node | نتیجهٔ اصلی blind | ارزیابی جدا با قواعد جاری | abstain |
|---|---|---|---|
| 637 | REJECTED، umbrella reason اصلی محفوظ | L1 PASS تشخیصی | بله |
| 1243 | REJECTED / L1_QUOTE_NOT_FOUND | PASS پس از wrapper amendment | خیر |
| 130 | REJECTED / RETURNED_MODEL_MISMATCH | identity و L1 PASS تشخیصی | خیر |
| 682 | COMPLETED / L1 PASS | سه quote exact | خیر |
| 2396 | COMPLETED / L1 PASS | پاسخ معتبر abstain | بله |
| 653 | REJECTED / L1_QUOTE_NOT_FOUND | یک quote با اختلاف case؛ FAIL باقی ماند | خیر |

مخرج‌ها: شش blind HTTP200/JSON قابل‌پارس، دو original COMPLETED، پنج current-rule L1 PASS شامل reassessment، دو abstention و سه non-abstaining L1-valid برای review. دو comparison attempted، هر دو original FAIL؛ صفر training label پذیرفته‌شده.

هشت HTTP200 phase response جمعاً ۸۰۲۰ input و ۱۵۶۲ output، شامل ۱۰۸۹ reasoning داشتند؛ input+output=۹۵۸۲. برآورد با نرخ اعلامی ۰٫۰۰۱۵۸۳ دلار است؛ invoice تأییدشده نیست. دو HTTP rejection اولیه خارج از این هشت‌اند و billing آن‌ها UNKNOWN است؛ «هشت پاسخ» کل تلاش‌های HTTP تاریخچه نیست.

کدهای قدیمی Colab الزام exact evidence فعلی را نداشتند؛ برخی utilityهای عمومی historical retry داشتند، درحالی‌که runner کنترل‌شدهٔ matched و اجرای فعلی no-retry بودند. بنابراین هم «API قبلاً روان‌تر بود» و هم «الان validation بیشتری داریم» می‌توانند درست باشند؛ همهٔ مسیرهای تاریخی را یکسان توصیف نمی‌کنیم.

## ۱۴. دو مرحلهٔ انسانی متفاوت و مشکل closeout

### الف) شش case توسعه‌ای و پاسخ مشترک دو نفر

در مرحلهٔ نخست، مالک و دوستش برای شش case یک پاسخ مشترک تهیه کردند؛ نه دو مجموعهٔ مستقل. شش JSON به‌علت timestamp، declarationهای تأییدنشده و یک enum نامعتبر قابل import رسمی نبودند؛ binding متن/packet بررسی شده بود. این وضعیت به‌خودی‌خود اثبات استفادهٔ ممنوع از GT یا LLM نیست.

اصل پاسخ‌ها حفظ و به‌عنوان consensus development feedback ثبت شد: دو SUPPORTED، سه UNSUPPORTED و یک NOT_ASSESSED در نتیجهٔ کلی؛ صفر pair مستقل و صفر import رسمی. کمک آموزشی LLM و دیدن نظرهای مؤلف نیز محدودیت blinding بود. اجماع را نباید به دو رأی مستقل یا gold تبدیل کرد.

### ب) شش پاسخ تازه برای سه خروجی واقعی پایلوت

برای blindهای ۱۲۴۳،۱۳۰ و۶۸۲ بسته‌های خصوصی تازه با admin mapping جدا ساخته شد. ابزار closeout در ابتدا reason گرهٔ ۶۳۷ را اشتباه انتظار داشت؛ diagnostics نشان داد actual reason همان `INVALID_ENVELOPE_OR_USAGE` است. ابزار v1.1 اصلاح شد؛ اصل ledger عوض نشد.

پس از اجرای محلی `CLOSEOUT_CREATED`، شش packet/form به معنی شش داوری انجام‌شده نبود. سپس شش پاسخ تازه دریافت و با manifest محلی نگاشت شد؛ نتیجهٔ ثبت‌شده `RESPONSES_VERIFIED_READ_ONLY` است.

| node | نتیجهٔ دو reviewer | برداشت مجاز |
|---|---|---|
| 130 | هر دو supports و topic=yes | پشتیبانی معنایی مثبت در این review؛ اصل REJECTED احیا نمی‌شود |
| 682 | هر دو does_not_support و topic=no | quote واقعی می‌تواند برای موضوع اصلی کافی نباشد |
| 1243 | یک supports و یک does_not_support | اختلاف حل‌نشده دربارهٔ MDP/planning در برابر RL |

overall agreement=۲/۳، topic agreement=۲/۳ و quote agreement=۴/۶. این‌ها آمار توصیفی نمونهٔ کوچک و مشروط‌اند؛ accuracy یا نرخ عمومی موفقیت نیستند. استقلال در وضعیت `SELF_DECLARED_NOT_EXTERNALLY_VERIFIED` است.

schema کوچک closeout با نام `sara3.l2.human.response.v1` همان canonical `sara.l2.human_review.v1` چهاربُعدی نیست. validation این پاسخ‌ها، import رسمی به Shadow یا L2 runtime محسوب نمی‌شود. هیچ arbitration، label acceptance یا GCN training از آن‌ها انجام نشده است.

## ۱۵. از توقف انسانی به Automated Concordance و quarantine پیشنهادها

مالک تأکید کرد که هدف نهایی کاهش وابستگی به متخصص است؛ human review نباید شرط اجرای هر comparison یا پذیرش اجرایی هر node باشد. gate اختیاری `precomparison_l2_gate` برای audit حفظ شد، ولی مسیر خودکار opt-in جدا ساخته شد.

نسخهٔ `sara.arbitration.automated_concordance.v1` پس از دو پاسخ L1-valid و audit readback، سازگاری را می‌سنجد: class یکسان blind/compare، قرارداشتن class در frozen candidates، primary_topic یکسان پس از strip/casefold، حداقل یک supporting target quote مشترک و نبود counter-evidence، auxiliary warning یا uncertainty صریح. third-class، conflict و abstention پذیرفته نمی‌شوند.

این قواعد مستقل بودن مدل‌ها یا entailment معنایی را ثابت نمی‌کنند. یک quote نامرتبطِ تکرارشده ممکن است از screen عبور کند. topic lexical equality نیز semantic equivalence نیست؛ confidence همان confidence تاریخی نامزد است.

ابتدا خطر وجود `accepted=true` در کنار L2 NOT_ASSESSED شناسایی شد. قرارداد عمومی اصلاح شد:

```json
{
  "decision": "PROPOSE",
  "accepted": false,
  "training_class_index": null,
  "provisional_status": "PROPOSED",
  "l2_status": "NOT_ASSESSED",
  "semantic_validation": "NOT_PERFORMED"
}
```

adapter نسخه‌دار `sara.gcn.experimental_concordance_admission.v1` با report/frozen-pair hash فقط plan آزمایشی می‌سازد. در قرارداد موجود، فقط report آفلاین با `provider_calls=0` را می‌پذیرد؛ live report خودکار training-admit نمی‌شود. تغییر این مرز به contract جدا نیاز دارد.

## ۱۶. Runner پایدار، CI و اجرای synthetic/fake روی Cora واقعی

مسیر واحد Rich V2 با SQLite journal، content-addressed audit، request/context binding و resume ساخته شد. completed معتبر پس از readback قابل replay است؛ uncertain/rejected خودکار retry نمی‌شود. تغییر prompt/model/context باید resume ناسازگار را مسدود کند.

روی authentic140 و R0/37، synthetic runner تعداد ۳۷ blind و ۳۷ compare، یعنی ۷۴ fixture dispatch داشت. اجرای دوم صفر dispatch و ۷۴ replay با report/GCN-plan hash یکسان داشت. نتیجه: ۹۳ baseline retained و پنج proposal مصنوعی؛ potential coverage=۹۸/۱۴۰=۷۰٪. این پنج proposal نتیجهٔ واقعی LLM نیستند.

سپس bridge GapGPT با fake HTTP نیز ۷۴ phase completed و اجرای دوم صفر dispatch/۷۴ replay داشت؛ ۹۳ baseline و پنج proposal مصنوعی باقی ماندند. usage و dollar estimate آن اجراها fixture هستند، نه مصرف provider.

اولین GitHub Actionsِ commit `387573a` واقعاً FAIL شد؛ شش مجموعه به artifact خصوصی دسترسی نداشتند. workflow بعدی در `a1b8444` public regression را از private pilot tests جدا کرد. سبزشدن CI بعدی شکست قبلی را پاک نکرد و ۷۳ SKIP معادل ۷۳ PASS نیست. CI عمومی موفق نیز جای full private regression ویندوز را نمی‌گیرد.

## ۱۷. اجرای واقعی Rich V2؛ درخواست اجرای کامل و آنچه واقعاً رخ داد

در تاریخچه، مالک اجرای batch مشخص و سپس GT evaluation و GCN را درخواست و اجازهٔ تاریخی داده بود. داشتن این درخواست اثبات انجام آن مراحل نیست. اجرای واقعی در سیستم مالک انجام شد؛ خلاصه‌های ترمینال به گفتگو برگشتند. این درخواست کنونی فقط خواندن و نوشتن خلاصه است و آن مجوزها را دوباره فعال نمی‌کند.

قرارداد اصلی: Cora140، R0، budget37، سقف۷۴ call، GapGPT، `gpt-6-luna`، temperature1/n1، Rich Prompt V2، Automated Concordance V1، human gate خاموش، no third-class acceptance، no automatic retry و بودجهٔ اعلامی ۰٫۴۰ دلار.

بررسی tariff مانع مدتی بود. سپس با دستور صریح مالک، اجرای scoped بدون ادعای verified بودن tariff/retention فراهم شد؛ owner consent با provider verification یکی نیست. endpoint/model/usage برگشتی همچنان provider-reported هستند.

### batch اول با max_tokens=512

یک blind برای node25 ارسال شد: HTTP200، model alias مجاز، finish_reason=length، input1522، output512، reasoning512 و content صفر character. تمام سقف output صرف reasoning شده بود؛ Rich JSON کامل تولید نشد. ledger: صفر COMPLETED و یک REJECTED با `TRUNCATED_OR_NONFINAL`.

usage صفر summary فقط completedها را می‌شمرد؛ به معنی رایگان بودن نبود. برآورد raw envelope با نرخ اعلامی ۰٫۰۰۰۴۰۸۲ دلار بود؛ billing واقعی تأیید نشد.

### amendment مستقل max_tokens=4096

افزایش سقف خروجی explicit، نسخه‌دار و با تأیید مالک انجام شد؛ config و journal قبلی حفظ شدند. context و contract جدید:

```text
context: c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8
gateway: 59fd3de634a4aabae97fc9df02c396c5c435819e8b7f4cdbde1fe7837a8c165f
```

declared input cap=32768، max_tokens=4096 و timeout120 بود؛ wire byte preflight اندازه‌گیری tokenizer واقعی provider نیست. reasoning_effort صریح همچنان omitted بود.

### آخرین نتیجهٔ واقعی

| معیار | مقدار |
|---|---:|
| actual dispatch/response | 53 |
| blind COMPLETED | 29 |
| compare COMPLETED | 23 |
| compare REJECTED | 1 |
| UNCERTAIN | 0 |
| blind abstention میان completed blindها | 5/29 |
| compare abstention میان completed compareها | 1/23 |
| baseline retained | 93/140 = 66.4286% |
| provisional_count | 0 |
| routed training label جدید | 0 |

توقف node1814 compare به‌علت یک quote مشترک در supporting و counter evidence بود. HTTP200، finish stop، JSON parseable و model identity مجاز بودند؛ L1 به‌درستی طبق contract موجود `L1_DUPLICATE_EVIDENCE` داد. این failure به‌تنهایی wrong class یا fabrication را ثابت نمی‌کند.

handoff گزارش می‌کند هر ۵۲ completed دوباره L1 PASS گرفت و duplicate rejection نیز بازتولید شد؛ ۵۳ binding request/wire/raw/context و ۱۰۹ receipt JSON این batch بررسی شدند. این‌ها بررسی L1 و integrity هستند، نه semantic L2.

هشت blindِ همین batch هنوز dispatch نشده‌اند: `2487,2396,2238,2317,2022,2379,2490,2534`. داشتن پاسخ برای بعضی IDs در پایلوت legacy به معنی انجام Rich V2 request نیست؛ prompt/schema/context فرق دارد.

reasonهای گزارش routed شامل third-class diagnostic=۷، auxiliary warning=۵، blind abstention=۵، unresolved counter-evidence=۱۰، verifier abstained=۱، duplicate=۱ و not-attempted=۸ است. برای هشت مورد آخر، report فعلی reasonِ timeout می‌دهد، درحالی‌که intent ندارند و uncertain صفر است؛ باید `NOT_ATTEMPTED_AFTER_HALT` یا معادل روشن گزارش شوند.

### usage و هزینه با مخرج درست

| scope | input | output | reasoning داخل output | estimate USD با نرخ اعلامی |
|---|---:|---:|---:|---:|
| 52 COMPLETED | 79,337 | 32,297 | در summary جدا نشده | 0.0240822 |
| 1 REJECTED، node1814 compare | 1,423 | 895 | 687 | 0.0005898 |
| همهٔ 53 response | 80,760 | 33,192 | 18,619 | 0.0246720 |

نرخ‌های اعلامی ۰٫۱۰ دلار/M input و ۰٫۵۰ دلار/M output هستند؛ invoice/tariff واقعی Gateway مستقلاً تأیید نشده‌اند. reasoning دوباره به output اضافه نمی‌شود. reserved upper برای ۵۳ attempt برابر ۰٫۲۸۲۲۱۴۴ دلار و رزرو نظری ۷۴ attempt برابر ۰٫۳۹۴۰۳۵۲ دلار است؛ این‌ها خرج واقعی یا provider guarantee نیستند.

returned model در همهٔ ۵۳ پاسخ: ۲۳ alias و ۳۰ dated revision. پذیرفتن این دو رشته تصمیم محدود execution contract است، نه اثبات upstream identity.

## ۱۸. GCN آماده‌شده و کار انجام‌نشده

طرح downstream، CE/noPS را primary و WCE/noPS را supplementary نگه می‌دارد. WCE پس از شواهد exploratory قبلی انتخاب شده و نباید preregistered از ابتدا معرفی شود.

قرارداد ثبت‌شده: دو لایه GCN، hidden64، dropout0.5، ReLU، بدون batchnorm، Adam با lr0.01 و weight_decay0.0005، سی epoch، last checkpoint، بدون validation/early stopping و seedهای matched صفر تا نه. feature L2 normalization و min-max confidence weighting حفظ می‌شوند؛ constant confidence به ones می‌رود و WCE برابر `mean(CE_i*w_i)` است، نه تقسیم بر sum weights.

test همان ۲۵۶۸ complement کل۱۴۰ است؛ excluded یا abstained selected node به test منتقل نمی‌شود. برای مطالعهٔ SARA باید coverage، class distribution و در صورت کاهش coverage کنترل coverage-matched نیز دیده شود.

کلاس GCN تاریخی reviewed reuse شده و forward مصنوعی کوچک PASS گزارش شده است. **GCN واقعی با خروجی SARA-3، raw accuracy تازه و اثر causal یا generalization در آخرین شواهد انجام/تأیید نشده‌اند.** batch ناتمام و adapter آفلاین فعلی، این حلقه را خودکار کامل نمی‌کنند.

## ۱۹. آخرین وضعیت تست‌ها و بدهی‌های روشن

افزایش تعداد تست‌ها در طول تاریخچه نشان‌دهندهٔ checkpoints مختلف است. ۹۱/۹۲، ۱۰۱/۱۰۲، ۳۴۵/۳۴۷ یا CI عمومی سبز، جای آخرین full regression را نمی‌گیرند.

handoffِ ۵ نوامبر نتیجهٔ نهایی guarded local suite را چنین ثبت کرده است: **۴۲۲ تست، ۴۱۸ PASS، یک FAIL، یک ERROR، دو SKIP؛ زمان 207.344 ثانیه.** شبکه و دسترسی به actual human-sessionها guarded بوده‌اند؛ این اجرا dispatch واقعی نداشته است.

دو مسئلهٔ حل‌نشدهٔ snapshot:

1. تست robustness هنوز `pipeline.route_r0` را patch می‌کند، اما production از `pipeline.select_router` استفاده می‌کند. fixture injection به selector جدید نمی‌رسد؛ اختلاف call expectation به‌تنهایی خرابی router یا L1 را ثابت نمی‌کند.
2. diagnostic tampering test و helper از `with sqlite3.connect(...)` بدون explicit close استفاده می‌کنند. این context manager transaction را مدیریت می‌کند؛ connection الزاماً بسته نمی‌شود و Windows cleanup با WinError32 روی sqlite lock خطا می‌دهد. سابقهٔ رفع مشابه در تست قدیمی وجود دارد، اما مسئلهٔ جدید را حل‌شده فرض نمی‌کنیم.

دو skip مربوط به POSIX permission روی Windows و مجوز filesystem symlink هستند؛ ZIP symlink rejection جدا تست می‌شود. اجرای اولیهٔ sandbox نیز errorهای ACL/cleanup داشت و PASS نبود؛ به‌قصد سبزکردن tests، ACL ضعیف نشده است.

همان ممیزی، syntax ۷۱ Python source و پنج utility را بدون اجرای CLIهایشان، ۱۴ تست JS و TypeScript noEmit، source/input/sealها و response bindingها را بررسی کرده بود. **این خلاصه این checks را دوباره اجرا نکرده است.**

## ۲۰. Git، backup، محیط و شیوهٔ کار

در شروع recovery، remote نبود؛ سپس کاربر repo `Parand1khalili/LLM-GNN` را ساخت و pushهای دستی در تاریخچه ثبت شد. بعد از مقطعی push مستقیم از چت دیگری نیز گزارش شده است؛ این‌ها رویدادهای تاریخی‌اند، نه مجوز push در این نوبت.

در زمان نگارش، root/main/HEAD و remote configuration محلی دوباره خوانده شد. remote=`https://github.com/Parand1khalili/LLM-GNN.git` و HEAD و local trackingِ origin/main هر دو `2373b9685b195080d81f3fcecd88001a9b04a8ff` بودند. برابری local tracking، بررسی زندهٔ remote، private visibility یا backup مستقل نیست. fetch، ls-remote و push در این نوبت انجام نشد.

پنج utility untracked کاربر محفوظ‌اند: `closeout_sara3_feasibility.py`، `diagnose_closeout_readiness_v2.py`، `diagnose_gapgpt_post130.py`، `diagnose_sara3_closeout_readonly.py` و `verify_human_l2_readonly.py`. handoff و JSON audit نیز از قبل untracked بودند. blanket-stage یا حذف آن‌ها مجاز تلقی نشد.

آرشیو تاریخی Drive حفظ شده، ولی dedicated backup جدید، destination تأییدشده و upload/readback در شواهد نهایی ثبت نشده است. `PLANNED_NOT_UPLOADED` و local sync folder، backup نیستند. GitHub code backup نیز raw responses، private journals و artifactهای خارج Git را پوشش نمی‌دهد.

محیط جدید ثبت‌شده Python3.12.14، Torch2.15.0+cpu، PyG2.7.0، NumPy2.3.5 و tiktoken0.14.0 است؛ با successful environment تاریخی Python3.13.16/Torch2.11.0+cpu/NumPy2.1.3 یکی نیست. خطای TLS اولیه با trust root معتبر رفع شده بود، نه با خاموش‌کردن verification. بازاجرای environment.yml یا startup قدیمی بدون review توصیهٔ این سند نیست.

در تاریخچه، Caveman و Ponytail برای گزارش کوتاه، استفاده از کد موجود و مهار پیچیدگی مطرح و نصب شدند. تقسیم کار بین فهم علمی، تسک محدود coding و verification برای کاهش مصرف مدنظر بود؛ compact سهمیه را reset نمی‌کند. این ترجیح نباید باعث حذف تست ضروری یا نوشتن ادعای علمی ضعیف شود.

## ۲۱. مهم‌ترین اصلاح‌های برداشت در طول مسیر

| برداشت ناقص یا قدیمی | جمع‌بندی درست پس از دنبال‌کردن تاریخچه |
|---|---|
| «دو مدل مستقل B1/v0 داریم» | دو prompting arm از همان مدل پایه‌اند |
| «۲۸۰ replay یعنی rawها کامل بازیابی شدند» | فقط stored parsed-sample voting تطبیق یافته است |
| «P0 همان شش blind/compare است» | P0 هشت node و ۱۲ logical arm record متفاوت است |
| «semantic فعلی همان R1 تاریخی است» | Semantic-v0 و R1/R2 candidateها reconstructionهای نام‌گذاری‌شده‌اند |
| «فقدان keyword یعنی ریسک خطای بالا» | missing coverage با observed mismatch فرق دارد؛ v2 این‌ها را جدا کرد |
| «HTTP200 یعنی پاسخ پذیرفته شد» | identity، schema، L1، audit و policy ممکن است رد کنند |
| «L1 PASS یعنی کلاس درست است» | ۶۸۲ نمونهٔ L1 PASS با review معنایی منفی است |
| «L2 مثبت یعنی ledger قبلی احیا می‌شود» | ۱۳۰ review مثبت دارد، اما REJECTED اصلی محفوظ است |
| «شش consensus، دو داوری مستقل‌اند» | شش پاسخ مشترک، صفر independent pair است |
| «Concordance همان L2 خودکار معتبر است» | screen سازگاری آزمایشی است؛ semantic validation انجام نشده |
| «۹۳ baseline، موفقیت Agent سوم است» | retention بدون review زیر قاعدهٔ بازسازی‌شده است |
| «پنج proposal قبلی در live هم وجود دارند» | آن پنج مورد synthetic/fake بودند؛ live اخیر صفر proposal دارد |
| «usage صفر rejected یعنی cost صفر» | completed-only summary مصرف rejected را ممکن است حذف کند |
| «کل گراف هنوز unavailable است» | topology کامل بعداً بازیابی شد؛ features/training جداست |
| «CI سبز یعنی همهٔ private tests پاس‌اند» | public CI با skip/exclusion محدود است؛ آخرین full suite سبز نیست |
| «درخواست اجرای کامل یعنی GCN انجام شد» | batch متوقف شد و نتیجهٔ تازهٔ GT/GCN احراز نشده است |

## ۲۲. دستاورد علمی قابل‌دفاع و سؤال‌های باز

شاهد مثبت historical: Narrative v0 در مطالعهٔ matched FeatProp موجود از B1 بهتر گزارش شده است، با بیشترین paired mean difference برابر +۲٫۵۷۰۰۹۳pp در Sensitivity/WCE/noPS. این شاهد به همان setting تعلق دارد و سود SARA-3 را نشان نمی‌دهد.

دستاورد recovery/engineering: baseline از parsed sampleها بازپخش شد، دادهٔ authentic به pipeline وصل شد، topology بازیابی شد، L1 و audit و ledger و resume تست شدند، prompt اصلاح شد، مسیر proposal از training جدا شد و اجرای واقعی با failureهای محفوظ قابل بررسی است.

یافتهٔ feasibility: شکست فنی و پشتیبانی معنایی دو سطح متفاوت‌اند؛ exact quote می‌تواند نامرتبط باشد، و رد فنی نیز لزوماً به معنی غلط‌بودن استدلال علمی نیست. این یافته‌ها کوچک، انتخاب‌شده و بعضاً post-observation هستند.

هنوز مشخص نشده است: SARA-3 چه تعداد correction صحیح/غلط می‌سازد؛ کدام router با budget منصفانه بهتر است؛ آیا blind-first+comparison از blind-only یا comparison-only ارزش افزوده دارد؛ Concordance چه نرخ false acceptance دارد؛ retention/class balance چگونه بر GCN اثر می‌گذارد؛ و آیا هزینهٔ افزوده با سود مستقل همراه است.

Cora140 قبلاً در E0/E1 و توسعه دیده شده است؛ حتی freeze قرارداد تازه آن را به holdout untouched تبدیل نمی‌کند. ادعای confirmatory/generalization نیازمند ارزیابی مستقل و پروتکل مناسب است. ده seed GCN عدم‌قطعیت annotation، selection یا LLM replicate را پوشش نمی‌دهد.

## ۲۳. ادامهٔ منطقی پس از این خلاصه

این فهرست پیشنهاد ادامه است، نه اقدام اجراشده یا مجوز تازه:

1. آخرین state/registry را با snapshot واقعی reconcile کنید؛ historical outcomes را بازنویسی نکنید. not-attempted را از timeout و completed-only usage را از all-attempt usage جدا کنید.
2. دو regression مشخص selector injection و SQLite lifetime را با کوچک‌ترین اصلاح آفلاین و tests مرتبط بررسی کنید؛ قواعد علمی یا L1 را برای passکردن node1814 شل نکنید.
3. partial live outcome، صفر proposal و محدودیت معنایی را مستند نگه دارید. برای review genuine Rich V2 و تصمیم بستن batch یا amendment بعدی، قرارداد prospective و baseline/control روشن لازم است.
4. برای هر اجرای بعدی، request scope/hash/context، no-redispatch check و مجوز لازم مشخص باشد؛ root جدید وسیلهٔ دورزدن halt نیست.
5. raw admission و backup artifact/code را تکمیل کنید؛ source recoveryهای موفق را از صفر تکرار نکنید.
6. فقط پس از freeze/admission مجاز، مطالعهٔ matched GT/GCN و کنترل coverage را اجرا و نتایج واقعی را گزارش کنید؛ سپس جداول پایان‌نامه و GraphScope را با provenance به‌روز کنید.

پیشنهاد نخست برای نوبت بعد: **reconcile گزارش آخرین batch و رفع دو regression آفلاینِ معلوم، بدون API یا training تازه.**

## ۲۴. نقشهٔ مراجعه برای ادامهٔ کار

| موضوع | مسیر در مخزن |
|---|---|
| snapshot کامل ۵ نوامبر | `docs/PROJECT_HANDOFF_2026-11-05_FA.md` |
| ممیزی ماشینی همان snapshot | `reports/PROJECT_HANDOFF_AUDIT_2026-11-05.json` |
| قواعد و state | `AGENTS.md`، `PROJECT_STATE.md`، `EXPERIMENT_REGISTRY.jsonl` |
| تفکیک مقاله/پروپوزال/بازسازی | `docs/SCIENTIFIC_PROTOCOL.md` |
| provenance و inputs | `manifests/recovered_sources.json`، `frozen_artifacts.json`، `authentic_inputs.json` |
| raw recovery | `docs/RAW_RESPONSE_RECOVERY.md` و `scripts/verify_intake.py` |
| L1 و Rich | `sara3/evidence.py`، `rich_evidence.py`، `pipeline.py`، `audit.py` در package |
| L2 | `evaluation/l2_benchmark.py`، `l2_reviews.py`، `l2_shadow.py` و `docs/L2_*.md` |
| Routerها | `sara3/r1_candidate.py`، `r1_coverage.py`، `r2_candidate.py`، `selection.py` |
| runner و live bridge | `sara3/runner.py`، `gateway_run.py`، `gapgpt_live.py`، `gateway_preflight.py` |
| diagnostic آخرین توقف | `sara3/gateway_diagnostics.py` |
| config آخرین batch | `configs/gapgpt_rich_v2_output4096_proposed.json` |
| خروجی خصوصی batch 4096 | `.local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105`؛ خارج از Git |
| downstream | `downstream/plan.py`، `model.py`، `frozen.py`، `prospective.py` |
| رابط و topology | `web/graphscope/VERIFICATION.md` و `TOPOLOGY_RECOVERY.md` |

فرمان live یا continuation در این خلاصه تکرار نشده است؛ وجود دستور historical به معنی امن‌بودن اجرای دوبارهٔ scope شروع‌شده نیست.

## ۲۵. ثبت بررسی همین نوبت و fingerprint منابع

در این نوبت منابع برای تهیهٔ خلاصه بررسی شدند، root/main/HEAD/history/remote configuration و نام فایل‌ها خوانده شد و این فایل نوشته شد. هیچ paid inference، training، GT decoding، credential access، private human-form intake، ویرایش ledger، historical artifact، push، fetch یا upload Drive انجام نشد. تست‌های علمی و regressionهای نقل‌شده متعلق به checkpoints منابع‌اند.

SHA-256 فایل‌های مبنا، محاسبه‌شده در زمان نگارش:

```text
PROJECT_HANDOFF_2026-11-05_FA.md
b25ece86eab240c665fbd64de09823a2345aef7073cf52e5c911d0ecb683d542

خلاصه بازیابی.txt
b1ffb74d222f3dda0353d3139e24386029be8a409b42b9998d4f2400c31de68e
```

این fingerprintها نسخهٔ منابع این خلاصه را مشخص می‌کنند؛ تأیید مستقل همهٔ ادعاهای داخل منابع یا تکمیل backup پروژه نیستند.
