# بازبینی علمی Router و Agent — ۲۰۲۶-۱۱-۰۸

**POST_HOC_DIAGNOSTIC / LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT**

این بررسی بعد از تکمیل مرحلهٔ اول و روی Aggregate همان تحلیل نوشته شد؛ هیچ
Router، Prompt، Rule، Threshold، K، Label، Admission یا Training تغییر نکرد.
فرضیه‌های حاصل از GT این Cohort تنها برای آزمون آینده روی دادهٔ مستقل‌اند.

## ۱. چه چیزی واقعاً می‌دانیم؟

|یافته|نوع شواهد|تفسیر مجاز و محدودیت|
|---|---|---|
|R0:22/37 خطادار در برابر23/103؛ R1:24/37 در برابر21/103|Diagnostic واقعی|Routerها مسئلهٔ پرخطا را غنی‌تر انتخاب می‌کنند؛ این به معنی قابلیت اصلاح آن نودها نیست|
|B1/Narrative:38 خطای مشترک؛36 توافق غلط|Diagnostic واقعی|Committee دارای هم‌بستگی خطاست؛ دو Prompt یک LLM، دو شاهد مستقل نیستند|
|Blind R0:19/30، R1:17/25 درست میان non-abstaining|Diagnostic واقعی|L1 PASS به معنی صحت موضوع یا کلاس نیست؛ Abstentionها جدا هستند|
|Consensus:4 Fix/4 Harm و2 Fix/2 Harm نسبت به Narrative|Diagnostic واقعی|توافق دو فاز روی این نمونه Net مثبت ایجاد نکرده است|
|P1-R0 به C،16 صحیح و9 غلط اضافه می‌کند؛ P2،17 صحیح و10 غلط|Diagnostic واقعی|Coverage بیشتر همراه نویز است؛ افزایش تعداد Label، سود GCN را تضمین نمی‌کند|
|GCN C→P1-R0:Fix52.8/Harm127.6 در هر Seed در Primary CE/noPS|Diagnostic واقعی روی Fitهای Frozen|بردار آموزشیِ تغییر‌یافته خروجی Test را بدتر کرده؛ علت را به یک Label خاص نمی‌توان نسبت داد|
|کنترل‌های هم‌تعداد Full GCN قبلی هم به نفع Agent نبودند|شواهد آزمایش قبلی؛ نه اجرای تازه|تفاوت صرفِ تعداد Label توضیح کامل نیست؛ در WCE وزن‌ها نیز دخیل‌اند|
|V2/Direct/V3 صفر Switch؛ V1-R0=C و P1-R1=P2-R1|برابری GT-free و Diagnostic|تنوع نام، تنوع عملکرد مستقل نیست؛ Fit یکسان باید بازاستفاده شود|

هیچ نقص عددی تازه در Training/Parser/L1 مشاهده نشد. این تحلیل جای اثبات نبود
تمام باگ‌ها یا Audit مستقل Encoder را نمی‌گیرد. آزمایش‌های GCN قبلی Admission
آزمایشی جداگانه داشتند؛ با «صفر Admission در اجرای اولیهٔ Live» مخلوط نمی‌شوند.
در این Slice هیچ Admission تازه‌ای انجام نشده است.

## ۲. تنظیم‌های واقعی؛ مقاله، دادهٔ مستقل یا Heuristic؟

|جزء|قرارداد واقعی|منشأ و محدودیت|
|---|---|---|
|R0|اختلاف Baseline اولویت دارد؛ سپس100−min(conf)، tie با Node ID؛ budget37|بازسازی مهندسی، نه تاریخیِ بایت‌یکسان و نه Risk کالیبره|
|Semantic-v0|Risk پایه +100×عدم تطابق بیشینهٔ Keyword کلاس‌ها|Heuristic واژگانی Atlas؛ Entailment یا معنای واقعی مقاله نیست|
|R1-v1|(disagreement+mismatch+ambiguity)/3؛ Missing هر دو term را1 می‌کند|وزن مساوی و maximal uncertainty ازپیش‌ثبت‌شده؛ absence را به ریسک زیاد تبدیل می‌کند|
|R1-neutral|Missing=0.5، همان ساختار امتیاز|Ablation تفسیری؛ تأیید مستقل ندارد|
|R1-v2|Missing semantic terms=0؛ Coverage به‌عنوان tie dimension جدا|اصلاح مفهومیِ ازقبل موجود، نه نتیجهٔ عملکرد واقعی Agent روی این Router|
|R2-v1|strata به‌ترتیب unknown4،observed17،candidate16؛ hash/version و backfill قطعی|Quota مهندسی و بدون GT تنظیم شده؛ هنوز پاسخ کامل Router-bound/نتیجهٔ واقعی ندارد|
|Budget37|پروتکل منجمد Router|عدد بهینهٔ هزینه/فایده اثبات نشده؛ کم‌کردن آن قرارداد جدید است|
|FeatProp|انتخاب140 هدف منجمد با Features/Graph|روش انتخاب، نه Toggle WCE/PS؛ شباهت به C-Density ادعا نمی‌شود|
|Blind/Comparison|Blind بدون رأی Baseline؛ Comparison با Candidate classها و کلاس واقعی Blind|وابستگی مرحله‌ای آشکار است؛ توافق دو فاز رأی مستقل نیست|
|Rich Prompt V2|EVERY quote، target.text، کپی دقیق capitalization/punctuation/whitespace؛ Class Atlas ثابت|ناسازگاری قدیمی «حداقل یک quote» را نباید به Prompt فعلی نسبت داد؛ از نظر معنایی ممکن است تفسیر غلطِ quote واقعی باقی بماند|
|L1/L2|همهٔ quoteها schema/source/exactness؛ L2=NOT_ASSESSED|Provenance validity لازم است، اما Semantic Support را ثابت نمی‌کند|
|Automated V1|دو فاز معتبر، بدون Counter/Warning/Uncertainty، Topic لفظاً برابر، quote مشترک، بدون Third-class|Screen مهندسی بسیار سخت؛ مستقل اعتبارسنجی نشده است|
|Weighted V2|2P+N+Q+T−A−2C−U؛ threshold3،third4، شرط P یاN|Defaults مهندسی؛ prototype حداقل5،cosine≥.20 وmargin≥.05؛ neighbor≥3 وsupport≥2/3 وdensity≥.10|
|Direct-seed|همان V2، بدون الزام اتصال داخلی همسایه‌ها|دادهٔ Seed مستقیم هنوز در74 مشاهده صفر است؛ مشکل فقط Density نبود|
|Evidence V3|2Q+2T+P+N−A−2C−U؛3/4؛ P/N اختیاری|وجود flag به‌عنوان penalty، Semantic Quality را اعتبارسنجی نمی‌کند|
|Consensus-only|توافق معتبر دو فاز و quote واقعی؛ Warning/Counter/Topic تشخیصی|Diagnostic Ablation پس از مشاهدهٔ V1–V3؛ روش تأییدی نیست|
|C|توافق دو Baseline با min confidence≥80؛ بقیه Abstain|آستانهٔ بازسازی‌شده، نه Probability تضمین‌شده|
|P1/P2|جدول تصمیم ثابت؛ P2 resolver/fallback محدود اضافه دارد|Hypothesis مهندسی و Frozen؛ Conditional Comparisonِ Abstaining دور زده نمی‌شود|
|WCE|Min-max confidence روی نمونه‌های نگه‌داشته؛ mean(weight×CE)|تأیید Calibration مستقل نداریم؛ یک Label می‌تواند وزن0 بگیرد|
|Missing-confidence Extension|وزن1 بدون ادعای confidence؛ PS نمونهٔ بی‌امتیاز را Protected نگه می‌دارد|روش آزمایشی جدا؛ وزن1 نسبت به known normalized weights می‌تواند اثر نسبی بیشتری بدهد|
|PS|حذف30٪، entropy pseudo-label، rank/tie/class guard ثابت|Guard تنوع را نگه می‌دارد، نه درستی Label را؛ singleton غلط می‌تواند باقی بماند|
|GCN|دو لایه64،dropout.5،Adam.01،decay.0005،30 epoch،seeds0..9|قرارداد تاریخی پروژه؛ نه بهینهٔ اثبات‌شده برای تمام سطح‌های نویز و Maskها|

R1-v1 هر30 مورد No-Atlas را انتخاب کرده:20 خطادار و10 دارای دو Baseline صحیح.
در Selected دارای Match،4/7 خطادارند. این نتیجه با «Keyword نبود پس قطعاً اشتباه
است» سازگار نیست. نبود Match با خطا هم‌بستگی دارد، ولی علت واژگان/طول متن/ژانر
از این Cohort جدا نمی‌شود. R1-v2 قبلاً این تفکیک مفهومی را انجام داده، اما در
نبود پاسخ‌های واقعی نباید موفقیت Downstream آن را ادعا کرد.

Wire واقعیِ احراز‌شده: GapGPT،gpt-6-luna،temperature=1،n=1،max_tokens=4096؛
reasoning_effort صریح در قرارداد نیست. نبود پارامتر به معنی غیرفعال‌بودن Reasoning
نیست. نام مدل/Revision گزارش Provider است، نه اثبات مستقل upstream. تغییر Sampling
Temperature یا Token Budget در این بررسی پیشنهادِ اجرا یا آزمایش داده نشد؛ اثر
علّی آن‌ها از نتایج موجود معلوم نیست. تنظیم‌های Baseline تاریخی لزوماً برابر
Verifier نبوده‌اند و مقایسهٔ الگوریتم با تکرار بایت‌یکسان مدل یکی نیست.

در16 تغییر Consensus، Warning و Counter هر16 بار حاضرند؛ Topic تنها یک بار
لفظاً برابر است. بنابراین Presence این flags در این کاندیداها discrimination
نمی‌دهد و برابری string هم Semantic Consistency نیست. عمومی یا موضوعی‌بودنِ هر
هشدار بدون روش معنایی معتبر مستقل تأیید نشده؛ به آن Gold Semantic Tag ندادیم.

Seedهای مجاز از توافق‌های Unrouted همین140 نود ساخته می‌شوند؛ نبود همسایهٔ Seed
به معنی نبود گراف یا نبود هموفیلی نیست. استفاده از GT2568 به‌عنوان Seed ممنوع
است. Prototypeهای کلاس‌های کم‌نمونه نیز از شواهد کم و pseudo-labelهای نویزی
ساخته می‌شوند؛ صفر Switch ناشی از چند Gate/penalty است، نه فقط نبود N.

## ۳. روش‌های پژوهشی مرتبط و قابلیت انتقال

منابع اصلی در۲۰۲۶-۱۱-۰۸ بررسی شدند؛ تطبیق با SARA در ستون سوم استنباط این گزارش
است، نه نتیجه‌ای که آن مقالات دربارهٔ این پروژه ثابت کرده باشند.

|روش و منبع اصلی|ایده|مسئلهٔ SARA و هزینه/محدودیت|
|---|---|---|
|[Query-by-Committee،Seung et al.1992](https://collaborate.princeton.edu/en/publications/query-by-committee/)|Query براساس اختلاف Committee|برای اختلاف B1/Narrative مناسب است، اما توافق غلط مشترک36 مورد را تضمینی نمی‌یابد؛ استقلال/تنوع Committee فعلی کافی فرض نمی‌شود|
|[Calibration،Guo et al.2017](https://proceedings.mlr.press/v70/guo17a.html)|تفکیک Confidence از correctness likelihood؛ Temperature Scaling برای Logitهای مناسب|Confidence رأی LLM کالیبره نیست؛ Scaling به Development مستقل نیاز دارد. Sampling temperature=1 با Calibration temperature یک چیز نیست؛ بدون Logit کامل، روش را مستقیم روی درصد رأی کپی نمی‌کنیم|
|[BatchBALD،Kirsch et al.2019](https://arxiv.org/abs/1906.08158)|Uncertainty و وابستگی نمونه‌های یک Batch، نه جمع‌کردن Top-K مشابه|Router ممکن است نودهای دشوارِ تکراری انتخاب کند؛ هدف diversity مفید است ولی posteriorهای موردنیاز و هزینهٔ محاسبه را فعلاً نداریم. این منبع Class Quota خاص SARA را اثبات نمی‌کند|
|[SelectiveNet،Geifman/El-Yaniv2019](https://proceedings.mlr.press/v97/geifman19a.html)|بهینه‌سازی Risk–Coverage با گزینهٔ Reject|C و V1 نشان می‌دهند Abstention مهم است؛ Label کمتر ممکن است آموزش را ضعیف کند. انتقال تضمین‌های آن به threshold80 یا یک LLMِ بدون Calibration مجاز نیست|
|[Co-teaching،Han et al.2018](https://arxiv.org/abs/1804.06872)|دو شبکه نمونه‌های محتملِ تمیز را مبادله می‌کنند|برای نویز Label مرتبط است، اما دو مدل و Training اضافی/فرضیات small-loss می‌خواهد؛ دو Prompt یک LLM معادل این روش نیستند؛ اولویت اصلاح کوچک فعلی نیست|
|[ALCE،Gao et al.2023](https://aclanthology.org/2023.emnlp-main.398/)|تفکیک کیفیت Citation از درستی/پوشش محتوای پاسخ|Quote واقعی می‌تواند Claim را پشتیبانی نکند؛ نیاز به سنجش entailment جدا دارد. ابزار آن Gold Semantic Gate برای کلاس‌های Cora به ما نمی‌دهد؛ LLM judge تازه اجرا نشد|
|[LLM-as-a-Judge،Zheng et al.2023](https://arxiv.org/abs/2306.05685)|Position،verbosity وself-enhancement bias|Comparison رأی‌های قبلی را می‌بیند و همان خانوادهٔ مدل است؛ anchoring یک فرضیه است نه علت اثبات‌شده. Counterbalance روی دادهٔ مستقل ممکن است هزینهٔ Comparison را دو برابر کند|
|[Correct and Smooth،Huang et al.2021](https://arxiv.org/abs/2010.13993)|استفاده از correlation و انتشار اطلاعات روی گراف|Neighborhood consistency تنها با Seed معتبر و فرضِ ارتباط Labelها معنی دارد؛ انتشار pseudo-label غلط خطا را هم پخش می‌کند. نتایج supervised آن مجوز استفاده از Test GT در SARA نیست|

Class-aware/تنوع: حفظ Coverage و گزارش Recall هر کلاس لازم است، اما Bonus برای
کلاس کم‌نمونه یا سهمیهٔ GT-based ممنوع است. تفاوت بین Class Coverage و Class
Correctness باید باقی بماند. Thresholdهای مدل‌های دیگر بدون Development مستقل
به این نمونه منتقل نمی‌شوند.

## ۴. فرضیه‌های A تا F؛ شواهد موافق، مخالف و نامعلوم

|فرضیه|موافق|مخالف/هزینه|نامعلوم و آزمون مجاز آینده|
|---|---|---|---|
|A:بودجه0/5/10/20/37|هزینه کمتر، امکان کاهش افزودن نویز|Node سخت ممکن است حذف شود؛ Risk بالاتر الزاماً fixable نیست|هیچ K برنده از Test فعلی انتخاب نشد. Kها و هزینه‌ها باید روی دادهٔ مستقل از قبل ثابت شوند؛ R1/R2 فعلی Budget37 را enforce می‌کنند|
|B:Abstention به‌جای افزودن Label|C نسبت به Narrative18 خطا را حذف می‌کند؛ V1-R1 از C ده Wrong وپنج Correct را حذف می‌کند|حذف29 Correct در C وکاهش Coverage؛ V1-R1 هنوز GCN مستقل اجرا نشده|مقایسهٔ selection با حذف بدون Agent و Coverage/class-count matched لازم است، نه فقط Selective Accuracy|
|C:تفکیک نبود Keyword و خطا|30 مورد Missing در R1-v1؛ ده مورد هر دو Baseline صحیح|واژگان همچنان ممکن است proxy مفید دشواری باشند|R1-v2 موجود است و نیاز به Router/Threshold جدید ندارد؛ باید prospective بررسی شود، نه بر مبنای errors فعلی برنده اعلام شود|
|D:Evidence-aware Fusion|L1 صحت Source را نشان می‌دهد؛ flags مشترک کم‌تفکیک‌اند|Semantic Gate مستقل نداریم؛ Topic string سخت‌گیر و Presence counter مبهم است|یک معیار معنایی معتبر لازم است؛ افزودن Heuristic لفظی تازه از روی16 نمونه، L2 معتبر نمی‌سازد|
|E:Confidence/Weighting|Confidence منشأ واقعی دارد؛ WCE گاهی بهتر است|Third-class وزن1 وPS Protected ممکن است نویز را نسبی تقویت کند؛ اثر همهٔ کلاس‌ها یکسان نیست|Calibration فقط روی Development مستقل؛ CE کنترل پایه بماند، هیچ Weight در این Cohort tune نشود|
|F:انتخاب محافظه‌کارانه|C در اجراهای اصلی از Fusionهای دارای افزودن Agent بهتر بود؛ Consensus Net صفر|C خودش21 خطای مشترک نگه می‌دارد و ضمانت صحت ندارد|C مرجع لازم است، نه راه‌حل نهایی؛ ارزش اطلاعات Agent باید با Control هم‌تعداد/هم‌کلاس‌تعداد سنجیده شود|

## ۵. سه مسیر اولویت‌دار، بدون پیاده‌سازی

|رتبه|مسیر|پشتوانه/سادگی|هزینه و خطر|
|---|---|---|---|
|1|آزمون نقش Agent به‌عنوان Abstention-only، بدون Switch کلاس، با C به‌عنوان Baseline|بررسی ارزش حذف Label از افزودن نویز جدا می‌شود؛ Rule جدیدِ tuned ساخته نمی‌شود|مقداری Label صحیح هم حذف می‌شود؛ نیاز به Control انتخاب هم‌تعداد. V1 فعلی ممکن است با Router-only removal یکسان باشد و در این صورت هیچ ارزش افزوده‌ای به Agent نسبت داده نمی‌شود|
|2|مقایسهٔ prospective همان R1-v2 موجود با R0، Coverage به‌عنوان Missingness|نقص مفهومیِ maximal-missing قبلاً رفع شده؛ بدون Router جدید|API برای موارد بدون پاسخ، Contract/reuse audit و دادهٔ مستقل لازم است؛ enrichment فعلی مجوز انتخاب برنده نیست|
|3|Calibration و حساسیت WCE/PS روی Development مستقل|Confidence وweighting توضیح‌پذیرتر می‌شود؛ از سیاست چندوزنی جدید پرهیز می‌شود|نیاز به Labels مستقل و جدایی Development/Test؛ مدل یادگیرندهٔ Calibration در این Slice ساخته نمی‌شود|

## ۶. آزمایش کوچک پیشنهادی برای مسیر۱؛ اجرا نشده

1. Cohort/متن/Graph و Test جدیدی انتخاب و ثبت شود که GT آن در تحلیل/توسعهٔ فعلی
   دیده نشده است. جابه‌جایی Nodeهای همین Cora یا نام‌گذاری مجدد2568 تست، استقلال
   ایجاد نمی‌کند. شش Consensus Development Case هم Holdout مستقل نیستند.
2. B1/Narrative مجاز با منشأ/Confidence معتبر Freeze شوند؛ C همان agreement80
   باشد. این عدد تغییر نمی‌کند. اگر Baselineها موجود نباشند، هزینهٔ ساخت آن‌ها
   جداگانه تصویب شود؛ پاسخ جدید یا معادل تاریخی جعل نمی‌شود.
3. برای Feasibility فقط top10 همان رتبه‌بندی R0، به‌دلیل سقف منابع20 فراخوانی
   Agent، پیشنهاد می‌شود؛ **نه به‌عنوان K بهتر**. تغییر Budget و Seal به مجوز و
   قرارداد مستقل نیاز دارد. روی GT فعلی K-sweep یا انتخاب Threshold انجام نشد.
4. سه Arm ازپیش‌ثبت‌شده: C؛ C با حذف مواردی که Screen منجمد V1 نتواند از آن‌ها
   حمایت کند (فقط veto/abstain، بدون Label تازه)؛ و Control بدون Agent با همان
   تعداد حذف در هر pseudo-class، انتخاب‌شده با Hash ثابت قبل از GT. Guard عدم
   حذف آخرین عضو کلاس ازپیش مشخص و یکسان باشد، نه بر اساس کلاس‌های خطادار فعلی.
5. Exact-ID control نیز به‌عنوان Identity Check گزارش شود: اگر فقط Label حذف
   شده باشد، نگه‌داشتن دقیق همان IDs/Classes، Training یکسان می‌دهد. تکرار Fit یا
   انتساب این برابری به هوشمندی Agent ممنوع است. Router-only removal هم اگر
   Mask یکسان داد، Alias است و Fit جدید نمی‌گیرد.
6. Schema/L1، Prompt و پارامترهای Phase ثابت بمانند؛ L2 همچنان NOT_ASSESSED است.
   استفاده از پاسخ فقط با هویت کامل Request/Dependency و provenance مجاز است؛
   هیچ Semantic Approval اختراع نمی‌شود. سقف20 Generation مربوط به Agent است،
   نه تضمین صورتحساب یا تعداد واقعی Comparison پس از Abstention.
7. Endpoint اصلی قبل از GT: Risk–Coverage با تعریف fixed-class metrics و نرخ
   حذف Correct/Wrong در Evaluation جدا؛ سپس CE/noPS، همان Seeds0..9 و Training
   همسان، حداکثر30 Fit اگر سه Arm واقعاً متفاوت باشند. WCE/PS هم‌زمان تغییر نکنند.
   این سقف Feasibility است، نه Power Analysis یا تضمین کفایت حجم نمونه.
8. Freeze/Admission/Training/Evaluation و هزینه هرکدام مجوز جدا می‌خواهند.
   هیچ‌یک در این تسک اجرا نشده‌اند؛ نتیجهٔ صفر یا مضر نیز بدون Tuning حفظ شود.

نتیجه: Router مسئله‌های دشوار را پیدا می‌کند، اما Verifier/Fusion هنوز تبدیل آن
به Label بهتر را نشان نداده‌اند. قوی‌ترین مسئلهٔ اثبات‌شده، فاصلهٔ Provenance
Validation تا Semantic Correctness و افزودن Labelهای نویزی است؛ سهم دقیق Prompt،
دادهٔ ورودی و بایاس مدل هنوز فرضیه است. Training فعلی شاهدِ نقص اجرایی تازه نیست.
گزارش مرحلهٔ اول، JSONهای Aggregate و فایل‌های خصوصی، مبنای قابل‌ردیابی این
نتیجه‌اند؛ انتخاب نهایی روی Test تاریخی صرفاً Exploratory است.
