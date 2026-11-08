# انتقال جامع پروژهٔ LLM-GNN / SARA به چت بعدی

تاریخ: ۲۰۲۶-۱۱-۰۵، America/Los_Angeles. تهیه‌شده به درخواست مالک برای انتقال کار، پس از بازخوانی کد، Git، اسناد و شواهد محلی فعلی. این سند مجوز اجرای جدید نیست.

## ۱. نقطهٔ شروع چت بعدی؛ این بخش را اول بخوانید

- ریشهٔ واقعی: `C:\Users\Admin\Documents\ChatGPT\llm-gnn`؛ فقط شاخهٔ موجود `main`.
- HEAD هنگام ممیزی: `2373b9685b195080d81f3fcecd88001a9b04a8ff`، عنوان: `Add read-only private GapGPT L1 rejection diagnostics without response disclosure`.
- دیگر در مرحلهٔ «هنوز API اجرا نشده» نیستیم. پایلوت واقعی شش‌گرهی و دو batch جداگانهٔ Rich V2 اجرا شده‌اند. تمام آن‌ها باید از هم تفکیک شوند.
- اجرای Rich V2 با خروجی ۴۰۹۶ توکن پس از **۵۳ dispatch** متوقف است: **۵۲ COMPLETED، یک REJECTED، صفر UNCERTAIN**. ردشدگی: **گرهٔ ۱۸۱۴، مرحلهٔ compare، HTTP 200، `L1_DUPLICATE_EVIDENCE`**.
- هر ۵۲ پاسخ COMPLETED در ممیزی حاضر مجدداً از نظر ساختار و L1 روی target واقعی بررسی شدند و PASS گرفتند. پاسخ ردشده نیز همان خطا را بازتولید کرد. این نتیجه، ارزیابی معنایی L2 یا صحت کلاس نیست.
- batch متوقف را دوباره اجرا، reset یا با پوشهٔ جدید دور نزنید. این درخواست انتقال، مجوز ادامهٔ inference نیست.
- منطق جدید **Automated Concordance** اضافه شده، اما L2 نیست. پیشنهادهای routed در خروجی عمومی **`PROPOSE`، `accepted=false`، `training_class_index=null`** هستند.
- **۹۳ baseline label retained** در گزارش اجرای جدید، خروجی تأییدشدهٔ agent سوم نیستند؛ توافق‌های historicalِ بدون review تحت آستانهٔ بازسازی‌شدهٔ ۸۰ هستند. **provisional_count اجرای واقعی جدید صفر است**.
- شش پاسخ انسانی تازه برای سه خروجی واقعی پایلوت وجود دارند و اعتبارسنجی ساختاری شده‌اند؛ استقلال آن‌ها **SELF_DECLARED_NOT_EXTERNALLY_VERIFIED** است. این‌ها با شش پاسخ اجماعی قدیمی development فرق دارند.
- `PROJECT_STATE.md`، بخشی از README، registry و بعضی گزارش‌های قدیمی از وضع فعلی عقب‌اند. عبارت‌های `NOT_DISPATCHED`، «remote نداریم» یا «هیچ verifier واقعی نداریم» را وضعیت امروز فرض نکنید.
- نتیجهٔ ممیزی قابل‌پردازش: `reports/PROJECT_HANDOFF_AUDIT_2026-11-05.json`. اعداد این سند به snapshot فوق مربوط‌اند؛ HEAD و ledger را در شروع کار بعدی دوباره بخوانید.
- regression امروز **کاملاً سبز نیست**: ۴۲۲ تست، ۴۱۸ PASS، یک FAIL، یک ERROR و دو SKIP. دو مسئلهٔ selector test injection و SQLite cleanup در بخش‌های ۲۱ و ۲۴ مستند شده‌اند؛ قبل از توسعه/اجرای تازه بررسی شوند.

## ۲. قواعد دائمی و مجوزها

پاسخ‌ها فارسی؛ کد، identifier و commit انگلیسی. یک repository پیوسته؛ بدون directoryهای نسخه‌ای برای هر اصلاح معمولی. `AGENTS.md` را رعایت کنید، اما بخش‌های تاریخی آن را با دستور صریح و جدید مالک اشتباه نگیرید. مثلاً منع کلی inference در متن قدیمی، وجود inferenceهای مشخص و بعداً مجازشده را نفی نمی‌کند؛ همچنین مجوز batch قبلی، مجوز هزینه/dispatch تازه نیست.

محدودیت‌های فعال:

1. بدون branch، PR، push، force-push، remote جدید یا تغییر authentication. GitHub را مالک دستی push می‌کند.
2. بدون خواندن/decoding GT، correctness diagnostics برای runtime، تنظیم router با E0/E1، یا tuning با test set.
3. بدون GCN training واقعی یا evaluation واقعی جدید مگر با مجوز مجزا.
4. archive تاریخی Drive فقط خواندنی؛ raw response، split، frozen configuration، receipt و terminal ledger immutable.
5. API key فقط در محیط process یا prompt مخفی مجاز همان CLI؛ نه chat، source، argument، log یا Git. در ممیزی حاضر هیچ credential خوانده نشد.
6. بدون retry خودکار، replay پولی درخواست نامعلوم، fallback مدل/endpoint، یا identity تازه برای دورزدن failure.
7. فرم‌های ناتمام جلسهٔ قدیمی L2 را نخوانید؛ پاسخ دیگر reviewer را به reviewer نشان ندهید. داده‌ها و رسیدهای خصوصی وارد Git/GraphScope نشوند.
8. نتایج synthetic، consensus، خوداظهاری reviewer، historical report و اجرای واقعی مستقل را مخلوط نکنید.

## ۳. هدف علمی و تفکیک روش‌ها

هدف پایان‌نامه: annotation گره بدون GT با LLM، استفادهٔ کنترل‌شده از graph context، verification کلاس‌محور و نهایتاً بررسی اثر pseudo-label بر GCN.

- **B1**: baseline محلی text-only و paper-inspired؛ بازتولید دقیق B0 مقاله نیست.
- **Narrative v0**: annotation ساختارآگاه با context ثبت‌شدهٔ 1-hop؛ هر دو بازو از **همان LLM** استفاده کرده‌اند.
- **SARA-2 Policy 002**: چارچوب تاریخی confidence/agreement و judge؛ فرمول/threshold کامل تاریخی بازیابی نشده است.
- **SARA-3**: Atlas عمومی، router، blind-first verification، L1، تفکیک L2، arbitration محافظه‌کار و مطالعهٔ downstream.
- FeatProp برابر C-Density نیست؛ Uniform2Path3 هم random walk واقعی نیست.
- paper اصلی و proposal در `llm-gnn.pdf` و `40131012_proposal.pdf` هستند. نقشهٔ روش منتشرشده/پروپوزال/تاریخچه/بازسازی در `docs/SCIENTIFIC_PROTOCOL.md` ثبت شده است.

در تمام گزارش‌ها چهار لایه جدا بمانند: **L1 provenance، L2 semantic support، eligibility برای arbitration، اثر واقعی بر GCN**. PASS یکی، اثبات دیگری نیست.

## ۴. شروع recovery و چیزی که واقعاً از دست رفت

فرض معتبر مالک: کل workspace دوران Codex در `D:\SARA2` از دست رفته است؛ SARA-2، E0/E1، SARA-3، P0/P1/P2، کد، tests و ledgers آن دوران recovered executable محسوب نمی‌شوند. P2 فقط آخرین checkpoint گزارش‌شدهٔ تاریخی بود.

پایهٔ recovery، archive واقعی **pre-Codex Drive/Colab** است:

- Drive: [Prnd-project](https://drive.google.com/drive/folders/1u9eLA8uZVJxZsLi38h1-eDPhNDwj92ML).
- notebook اصلی: [Colab](https://colab.research.google.com/drive/1VTFrVkixOMmnkXEGWprtE7m4rSWuqJsY).
- archive در ابتدا با حساب دیگری shared شد؛ search connector و سقف ۱۰۰۰ آیتم به معنی حذف فایل نیست.
- ممیزی پذیرفته‌شده، notebook با ۵۶۸ سلول و ۵۴۵ سلول کد را گزارش کرده بود؛ هیچ سلولی برای recovery اجرا نشده است.
- ممیزی قبلی ۱۸۰ weight artifact را شناسایی کرده بود: ۱۶۰ fit FeatProp و ۲۰ fit agreement-only. در این نشست هر ۱۸۰ فایل مجدداً خوانده/verify نشده‌اند؛ این عدد را نتیجهٔ ممیزی تازهٔ همهٔ weights معرفی نکنید.
- snapshot upstream: `CurryTang/LLMGNN@1f60eedb1452cdd997be18b5dd932a02666ee57e`. upstream HEAD جای research modifications نیست و مقصد push پروژه هم نیست.

معنی provenance:

| وضعیت | معنی |
|---|---|
| RECOVERED_EXACT | bytes اصلی با hash معتبر تطبیق دارند؛ به‌تنهایی صحت اجرایی نیست |
| RECONSTRUCTED | کد/contract جدید از specification و شواهد ساخته شده است |
| REPRODUCED | یک محاسبه/خروجی با اجرای ثبت‌شده دوباره تولید شده است |
| UNVERIFIED / MISSING_EVIDENCE | هویت، وجود یا جزئیات دقیق هنوز اثبات نشده است |

## ۵. سورس‌ها، raw recovery و مرز reproducibility

`manifests/recovered_sources.json` شامل **۲۵ snapshot اصلی** است. هر ۲۵ hash در ممیزی حاضر مجدداً PASS شدند. تصحیح شمارش archive: داخل `src` تعداد ۴۳ فایل، شامل ۲۵ مشابه upstream، ۶ modified و ۱۲ added؛ `startup.py` بیرون src، سیزدهمین addition پژوهشی است. این شمارش با «۲۵ فایل انتخاب‌شدهٔ provenance در repository» یک مفهوم نیست.

سورسهای اصلی در `recovered_sources/` برای traceability نگه داشته شده‌اند؛ startup و scriptهای تاریخی با side effect اجرا/به‌طور کامل import نشده‌اند. Narrative pure module عین bytes اصلی reuse شده؛ voter، selectors، PS و GCN adapter از بخش‌های بررسی‌شده بازسازی شده‌اند. lineage در `manifests/implementation_lineage.json` است.

خام تاریخی:

- **۸۴۰ response reference** = ۷۲۶ fresh + ۳۰ supplementary + ۸۴ reused.
- ۴۸ reused در `manifests/unresolved_raw_responses.json` هنوز **unresolved access، نه proven missing** هستند.
- گزارش intake قدیمی `missing_raw_count=840` به معنی نبود bytes در intake آن اجراست؛ اثبات گم‌شدن archive نیست.
- replay فعلی، **stored parsed samples** را رأی‌گیری می‌کند؛ raw bodyهای ۸۴۰تایی را parse نکرده است.
- در recovery evidence اشاره به readbackهای قبلی وجود دارد، ولی در این ممیزی **صفر raw تاریخی از آن ۸۴۰** مستقلاً hash-admit شده است. پاسخ‌های API جدید pilot/batch مجموعه‌ای دیگرند.
- هیچ ZIP کامل بازیابی‌شده و admitشده‌ای در شواهد فعلی این بررسی احراز نشد. full raw admission همچنان باز است.

ابزارهای موجود:

- `scripts/colab_recover_responses.py`: یک cell مستقل برای Colab مالک archive، official interactive Drive mount، خواندن manifest موجود و مسیر واقعی، SHA-256، جلوگیری از traversal/symlink/duplicate conflict، ZIP خارج از archive، بدون body در log، بدون inference/GT.
- `scripts/verify_intake.py`: بررسی ZIP بدون extraction، hash/CRC/member allowlist و توقف روی conflict؛ هیچ substitute ساخته نمی‌شود.
- `docs/RAW_RESPONSE_RECOVERY.md`: روش دقیق. این گیت فقط برای raw parsing/byte-level claims باقی مانده؛ مالک قبلاً مانع full-840 را برای **offline implementation و parsed replay** برداشته است.

## ۶. baseline عملی و نتایج replay

package نصب‌پذیر `src/llmgnn_sara/` بازسازی شده است. در ممیزی امروز هر **۲۸۰ target-arm vote از ۱۴۰ target × دو arm** دوباره با frozen outputs تطبیق داد: کلاس/fallback دقیق و confidence با tolerance مطلق `1e-12`.

قراردادهای مهم voter:

- سه parsed sample برای هر node/arm؛ denominator شامل invalid sampleهاست.
- tie با اولین occurrence؛ confidence مطابق loop تاریخی، نه average معمولی جدید.
- all-invalid fallback مطابق آخرین sample و نزدیک‌ترین کلاس edit distance، confidence نصف می‌شود.
- malformed/nonfinite/out-of-range fail closed؛ پاسخ جدید یا raw گمشده تولید نمی‌شود.

PS/class guard:

- حذف sequential؛ rankها tie-average نمی‌شوند؛ tie با global node ID.
- آخرین عضو کلاس حذف نمی‌شود؛ retained order همان ترتیب manifest است.
- milestone قبلی چهار cohort-arm comparison را برای retained/deleted order، labels و confidence PASS ثبت کرده است.

انتخاب FeatProp frozen replay می‌شود، نه reselection ادعاشدهٔ byte-exact. selector جدید float64 نزدیک tieها لزوماً همان Torch float32 تاریخی نیست.

## ۷. ورودی‌های authentic و graph؛ مرحله‌ای که در چت‌های قبلی ممکن است جا مانده باشد

`io/project.py::load_project_inputs` **۹ JSON hash-pinned** را admit می‌کند: دو prediction، selection، preparation receipt و پنج فایل authentic شامل B1/Narrative prompts، neighborhoods، prompt receipt و request manifest.

- ۱۴۰ target text واقعی از wrapper همان B1 استخراج می‌شود.
- ۲۸۰ stored prompt با ۸۴۰ sample reference و prompt hashهای frozen تطبیق دارد.
- Narrative target attachment، neighbor IDs، local identifiers، degree، connected/disconnected pairs و token bounds بررسی می‌شوند.
- متن و neighborhood برای runtime از **recorded graph evidence** می‌آیند؛ جای اجرای مجدد کامل graph-feature/FeatProp/prompt regeneration معرفی نمی‌شوند.
- Atlas فعلی عمومی و بازسازی‌شده است: هفت تعریف و چهار keyword برای هر کلاس؛ مجموع ۲۸ keyword. معنای کلاس‌ها مجاز است، labels گره GT نیستند.

**canonical graph واقعاً بعداً بازیابی شد**، برخلاف برخی متن‌های قدیمی:

- فایل اصلی `cora_random_sbert.pt`، ۶٬۸۹۸٬۷۸۴ bytes، SHA-256:
  `9285c2afae1bdd9e01ee1b805ace7bd1308a49895b1f11fa22bd0e5bd0adf466`.
- commit `573b1e4`؛ شرح `web/graphscope/TOPOLOGY_RECOVERY.md`.
- استخراج ثابت و hash-bound با ZIP + `pickletools` metadata inspection؛ **نه unpickle، نه torch.load، نه اجرای pickle VM**.
- فقط edge storage خوانده شد؛ label storage خوانده یا decode نشد.
- ۲۷۰۸ node، ۱۰۸۵۸ directed tensor entry، ۱۰۵۵۶ unique directed، ۳۰۲ repeated directed، ۵۲۷۸ unique undirected، صفر self-loop/isolated.
- تطبیق ۱۴۰/۱۴۰ target text و target degree؛ وجود ۵۲۵/۵۲۵ research edge؛ node order حفظ شده است.
- topology خروجی `web/graphscope/public/data/full-topology.json` با hash:
  `031bb1d3ab26ed22477cbf6ecbdbb784309850448a291e21476faaaa12339820`.
- این milestone بازیابی topology است؛ به معنی بازتولید feature matrix، GCN training یا GT evaluation نیست.

ترتیب canonical کلاس‌ها، بدون تغییر:

```text
0 rule_learning
1 neural_networks
2 case_based
3 genetic_algorithms
4 theory
5 reinforcement_learning
6 probabilistic_methods
```

## ۸. نتایج علمی تاریخی موجود؛ نه نتیجهٔ training تازه

جدول زیر از export موجود GraphScope که از scalarهای تاریخی ساخته شده خوانده شد. هر condition شامل دو arm × ده matched seed است؛ ۸ condition مجموعاً ۱۶۰ fit دارد. SD مربوط به training seed است، نه تکرار مستقل LLM.

| Cohort / Loss / PS | تعداد train هر arm | B1 mean ± population SD (%) | Narrative v0 mean ± SD (%) | paired delta mean ± SD (pp) |
|---|---:|---:|---:|---:|
| Primary / CE / noPS | 135 | 69.680685 ± 0.411816 | 70.954050 ± 0.412644 | +1.273364 ± 0.368212 |
| Primary / CE / PS | 95 | 70.735981 ± 0.543849 | 71.911994 ± 0.432944 | +1.176012 ± 0.510348 |
| Primary / WCE / noPS | 135 | 70.486760 ± 0.322739 | 72.671340 ± 0.528448 | +2.184579 ± 0.380526 |
| Primary / WCE / PS | 95 | 70.097352 ± 0.597573 | 72.017134 ± 0.609570 | +1.919782 ± 0.688504 |
| Sensitivity / CE / noPS | 140 | 69.844237 ± 0.404385 | 71.732866 ± 0.458593 | +1.888629 ± 0.455208 |
| Sensitivity / CE / PS | 98 | 71.024143 ± 0.310771 | 71.974299 ± 0.323021 | +0.950156 ± 0.203240 |
| Sensitivity / WCE / noPS | 140 | 70.595794 ± 0.344555 | 73.165888 ± 0.448564 | +2.570093 ± 0.273141 |
| Sensitivity / WCE / PS | 98 | 71.460280 ± 0.403352 | 72.305296 ± 0.482866 | +0.845016 ± 0.334098 |

از handoff تاریخی: B1 annotation برابر ۹۶/۱۴۰ و Narrative برابر ۱۰۱/۱۴۰ گزارش شده است. این‌ها **HISTORICAL_REPORTED** هستند؛ در این ممیزی هیچ label GT باز نشده یا accuracy محاسبه نشده است. عدد ۷۶٫۲۳٪ مقاله مربوط به setup مقاله است، نه مقایسهٔ head-to-head با ۷۳٫۱۶۶٪ محلی.

E0/E1 تاریخی exploratory/post-GT بودند. عددهای خطای آن گزارش‌ها تنها سابقهٔ انگیزهٔ پژوهش‌اند؛ نباید وارد router، Atlas، prompt، threshold یا selection شوند. بازتولید دقیق E0/E1 یا تعمیم‌پذیری از آن‌ها ادعا نشده است. برای M1–M4 و agreement-only شواهد تاریخی هست، اما این نشست همهٔ source artifactها و نتیجه‌های عددی آن‌ها را مجدداً verify نکرده است.

## ۹. SARA-2، R0 و historical P0

PolicyConfig فعلی **RECONSTRUCTED_POLICY_NOT_HISTORICAL_EQUIVALENT** است. آستانهٔ agreement retention برابر ۸۰ درصد و R0 رتبه‌بندی confidence/agreement، پیش‌فرض‌های uncalibrated جدیدند؛ دقیقاً recovered Policy002 نیستند. داشتن hash یک policy گزارش‌شده، بازیابی محتوای آن نیست.

Historical P0 محفوظ است:

- Group A: `734,2379,2490,682`؛ هر node یک `Judge002` و یک `SARA3_V1`، مجموع ۸ logical record.
- Group B: `1031,655,1013,1328`؛ فقط `SARA3_V1`، مجموع ۴ logical record.
- **۸ unique node و ۱۲ logical (node,arm) record**، شامل ۴ Judge002 و ۸ V1.
- هر هشت ID در cohort frozen معتبرند؛ Group B agreement/HH با convention >=80 بررسی شده است. historical R1 membership همچنان reported/unverified است.
- `manifests/historical_p0.json` با hash ثابت
  `7affacee222dbec3ecb5710b038968543c19d252190ee6eab76c5b03a4307410` در ممیزی امروز PASS شد.
- `docs/HISTORICAL_P0_ARM_CONTRACTS.md` field-level matrix دارد: EXACT_MATCH، BEHAVIORAL_MATCH، RECONSTRUCTED، PROTOCOL_DELTA، MISSING_EVIDENCE.
- Judge002 prompt/schema، جدول تصمیم تاریخی کامل، original P1 wire و رابطهٔ logical record با تعداد generation واقعی بازیابی نشده‌اند. **فرض دو call برای V1 تاریخی نکنید.**
- شش‌گرهٔ feasibility بعدی P0 تاریخی نیستند. هیچ اجرای paired Judge002/V1 تاریخی در این recovery اثبات نشده است.

## ۱۰. L1، private audit و conservative V1

سورس اصلی: `sara3/evidence.py`، `rich_evidence.py`، `pipeline.py` و `audit.py`.

- legacy response سه فیلد دارد: `class_index`, `abstain`, `evidence`.
- strict abstention: class=null و evidence خالی؛ contradiction reject می‌شود، نه silently repair.
- class ID معتبر، schema کامل، source ID/field/hash معتبر و quotation غیر trivial لازم است.
- quote باید exact substring همان authorized source باشد؛ source اشتباه، fabricate، تغییر word/case/punctuation/whitespace رد می‌شود.
- legacy و Rich V2 فعلی برای quotation فقط `target.text` را admit می‌کنند. وجود neighbor در context، مجوز quote از آن تحت source target نیست.
- حداکثر مجموع چهار evidence item؛ quote حداکثر ۵۱۲ character، lexical floor حداقل دو word و هشت character حروف/اعداد.
- duplicate normalized exact quote، حتی میان support/counter، فعلاً `L1_DUPLICATE_EVIDENCE` است.
- raw response و rejection diagnostics در private current-user ACL audit، جدا از training labels و GraphScope نگه داشته می‌شوند. audit failure fail closed است.
- Blind قبل از comparison audit و immutable می‌شود؛ blind input فاقد B1/v0 votes/confidence است.
- پاسخ هم‌کلاس با candidate به‌تنهایی مجوز training label نیست؛ third-class فقط diagnostic/audit-only است.

اصلاح محدود پس از مشاهدهٔ node1243:

`sara.l1.decorative_quote_match.v1` فقط برای matching یک outer pair کامل ASCII `"..."` یا curly `“...”` را حذف می‌کند. trim، casefold، fuzzy matching، semantic replacement، recursive stripping یا بازنویسی داخل متن ندارد. wrapper ناقص/نامتوازن/nested رد می‌شود. raw پاسخ اصلی عوض نشده است. این یک **post-observation rule amendment** است، نه نتیجهٔ اصلی همان روز.

کدهای مهم: `L1_SCHEMA_INVALID`, `L1_ABSTENTION_CONTRADICTION`, `L1_CLASS_INVALID`, `L1_UNKNOWN_SOURCE`, `L1_REFERENCE_MISMATCH`, `L1_TRIVIAL_QUOTE`, `L1_QUOTE_NOT_FOUND`, `L1_DUPLICATE_EVIDENCE`, `L1_GT_FIELD_FORBIDDEN`, `AUDIT_UNAVAILABLE` و `TIMEOUT_UNCERTAIN_NO_RETRY`.

## ۱۱. Rich schema و اصلاح prompt جدا از seal قدیمی

schema: **`sara.verifier.rich_evidence.v1`**؛ افزون بر class/abstain، شامل:

```text
primary_topic
supporting_evidence: [{source_id, quote, claim}]
counter_evidence: [{source_id, quote, claim}]
auxiliary_method_warning
uncertainty_reason
```

تمام supplied quoteها، از جمله counter-evidence، L1 می‌شوند. claim از نظر نوع/ساختار بررسی می‌شود، نه حقیقت یا entailment. L2 همواره NOT_ASSESSED است مگر assessment مستقل جداگانه ثبت شود؛ rich بودن JSON semantic proof نیست.

**مرحلهٔ جدید پس از چت قدیمی، commit `389af3b`:** prompt opt-in با version **`sara.verifier.rich_prompt.v2`**. legacy seal و rich-v1 prompt عوض نشده‌اند. V2 صریحاً برای **EVERY** support/counter item می‌خواهد target.text را contiguous، case/punctuation/whitespace-preserving و بدون decorative wrapper کپی کند. auxiliary method را از primary topic جدا می‌کند و third-class را diagnostic می‌نامد.

این اصلاح از ambiguity قدیمی «at least one exact quote» در برابر validator «every item exact» ناشی شد. V2 را هرگز payload تاریخی یا protocol شش‌گرهی قبلی معرفی نکنید.

## ۱۲. L2 rubric، benchmark، human review و Shadow

`sara.l2.rubric.v1` چهار بُعد دارد:

1. primary-topic relevance؛
2. quote→claim support؛
3. material counter-evidence resolution؛
4. auxiliary-method versus research-topic separation.

outcomeها: SUPPORTED / UNSUPPORTED / AMBIGUOUS / NOT_ASSESSED؛ judgment کلی را reviewer می‌نویسد، algorithm از رأی بُعدها نمی‌سازد.

شش-case development benchmark به‌صورت illustrative ساخته شد: narrow descriptive claim، copyright irrelevant quote، auxiliary-rule method promoted، finite-size contradiction، Bayesian/neural boundary ambiguity و title-only unassessed. این‌ها gold، holdout، independent review یا سنجش accuracy semantic judge نیستند.

workflow رسمی `sara.l2.human_review.v1` blinded packet، reviewer pseudonym، چهار dimension، rationale/evidence refs/timestamp و comparison دو reviewer دارد. متن author judgment، votes/confidence، GT و پاسخ reviewer دیگر پنهان می‌مانند. فرم readable نیز برای reviewer-a تهیه شد؛ جلسهٔ اصلی ناتمام در این ممیزی باز نشد.

Shadow **`sara.l2.shadow.v1`** فقط intake/evaluation خصوصی است؛ stateها **NOT_ASSESSED، ASSESSED، INVALID، UNAVAILABLE**. هیچ judge خودکار، label gate، adjudication یا تغییر router/arbitration ندارد. tests مصنوعی invariance را پوشش می‌دهند؛ synthetic assessment را human evidence نمی‌نامیم.

### سه مجموعهٔ انسانی را اشتباه نگیرید

**الف) شش case توسعه و پاسخ‌های اجماعی قدیمی:** مالک گفت پاسخ مشترک دو نفر است. صفر independent pair و صفر officially imported review از آن submissions؛ declarationهای تأییدنشده، مشکل UTC timestamp و یک rubric value نامعتبر ثبت شده بود. فقط exploratory development feedback؛ هیچ agreement metric مشروعی از consensus محاسبه نمی‌شود. originalها خصوصی و immutable‌اند.

**ب) closeout واقعی شش‌گرهی:** بعداً user scriptِ untracked به نام `closeout_sara3_feasibility.py` بستهٔ خصوصی ساخت:

- schema `sara3.feasibility.closeout.v1.1`؛ مسیر `.local_artifacts/sara3_feasibility_closeout_v1`.
- برای خروجی blind معتبر و non-abstaining گره‌های **۱۲۴۳،۱۳۰،۶۸۲** دو packet جدا A/B، مجموع شش packet.
- reviewer-case IDs تصادفی و mapping در admin؛ candidateهای historical/GT در reviewer packet نیستند.
- schema packet: `sara3.l2.blinded_case.v1`؛ schema پاسخ: **`sara3.l2.human.response.v1`**.
- این workflow محلی کوچک **همان schema canonical چهار‌بُعدی قبلی نیست**. per-quote support، overall support، primary-topic match، rationale و limitation دارد؛ هر چهار dimension رسمی را جداگانه جمع‌آوری نمی‌کند.

**ج) شش پاسخ تازهٔ همین closeout:** در `.local_artifacts/sara3_l2_responses_inbox` وجود دارند. با تابع بررسی‌شدهٔ `verify_human_l2_readonly.py::verify` در این ممیزی فقط aggregate استخراج شد:

- شش record structurally valid برای سه pair A/B؛ استقلال **خوداظهاری، نه externally verified**.
- overall agreement **۲ از ۳ case**؛ primary-topic agreement **۲ از ۳**؛ per-quote agreement **۴ از ۶ quote pair**.
- این اعداد descriptive هستند، نه accuracy، gold standard، causal evidence یا اثبات استقلال انسانی.
- این validator receipt hash، packet case binding، exact excerpt و تعداد quoteها را بررسی می‌کند؛ به‌تنهایی full scientific provenance و اصالت reviewer را اثبات نمی‌کند.
- از این read-only validation هیچ import به canonical human-review/Shadow، adjudication یا label acceptance انجام نشد. متن judgment، rationale، نام واقعی یا article اینجا کپی نشده است.
- جملهٔ «هنوز هیچ پاسخ انسانی واقعی وجود ندارد» دیگر درست نیست؛ جملهٔ «L2 runtime هنوز NOT_ASSESSED و training promotion نشده» همچنان درست است.

## ۱۳. Routerها؛ فرمول و تفاوت historical/new

همه GT-free، deterministic، class-order-fixed هستند. R1/R2 candidateها version مستقل دارند و دقیقاً historical R1/R2 recovered نیستند. برابرشدن counts مثل ۳۷/۱۸/۷، historical parity را ثابت نمی‌کند.

**R0 فعلی:** `100*disagreement + 100 - min(B1_confidence, Narrative_confidence)`؛ نزولی، tie با node ID صعودی. confidence درصد تاریخی و uncalibrated است.

**Semantic-v0:** اگر Atlas hit وجود داشته باشد، R0 به‌علاوهٔ `100*(max_hit - max_hit_of_two_candidates)/max_hit`؛ اگر hit صفر، fallback همان R0. semantic نام تاریخی/محلی دارد ولی در عمل lexical proxy است.

**R1-v1:** `D=1[a!=b]`، `h[c]=distinct keyword hits`، `m=max(h)`، `s=runner-up(h)`، `M=1-(h[a]+h[b])/(2m)`، `A=s/m`؛ risk=`(D+M+A)/3`. بدون match، M=A=1. این missing-evidence imputation باعث شد ۳۰ از ۳۷ selected بدون Atlas hit باشند.

missing-coverage policy review سه نسخه را بدون GT و بدون outcome tuning مقایسه کرد:

- v1 قدیمی حفظ شد؛ missing=maximal uncertainty.
- neutral: missing M=A=1/2؛ یک فرض midpoint، نه probability برآوردشده.
- **R1-v2**: observed risk=`(D+I[m>0]*(M+A))/3`؛ سپس coverage=`m/4` نزولی برای risk tie و سپس node ID. missing در diagnostics null است و positive mismatch evidence تولید نمی‌کند. unknown true risk را صفر اعلام نمی‌کند.

coverage states: NO_ATLAS_MATCH (`m=0`)، PARTIAL_COVERAGE (`m=1`)، OBSERVED_MULTI_KEYWORD_MATCH (`m>=2`). multi-keyword مساوی semantic support نیست. cohort شامل ۳۰ zero، ۵۱ partial و ۵۹ multi بود؛ mean word length به‌ترتیب 118.93،139.51،166.61. vocabulary/length bias باقی است؛ Atlas با known errorها expand نشد.

**R2-candidate-v1**: strata به‌ترتیب **U/O/C** و quota **۴/۱۷/۱۶** از بودجهٔ ۳۷:

1. unknown exploration: sort با SHA256 رشتهٔ `sara.router.r2_candidate.v1:explore:<decimal node ID>` و سپس ID؛ ۴ slot.
2. observed risk: matched Atlasها به order R1-v2؛ ۱۷ slot جدید.
3. candidate risk: R0 از باقی‌مانده‌ها؛ ۱۶ slot.
4. هر stratum overlap را skip می‌کند؛ exhausted pool سهم را زود منتقل نمی‌کند؛ آخر از global R0 deterministic backfill.

primary دادهٔ فعلی دقیقاً ۴/۱۷/۱۶ admission، ۲۱ overlap skip در candidate stage و صفر backfill داشت. hash exploration random sample آماری نیست.

### diagnosticها؛ نه error-detection performance

| Router؛ همه budget=37 | disagreement | HH agreement (>=80 convention) | Atlas unknown |
|---|---:|---:|---:|
| R0 | 9 | 0 | 11 |
| Semantic-v0 | 9 | 11 | 6 |
| R1-v1 | 7 | 15 | 30 |
| R1-v2 | 6 | 20 | 0 |
| R2-v1 | 9 | 9 | 10 |

- R1 primary overlap: v1/neutral=19، v1/v2=7، neutral/v2=25 از ۳۷.
- R2 overlap با R0=27، Semantic=26، R1-v1=17، R1-v2=19.
- تغییرهای prespecified quota در R2 چهاربار overlap=36/37 دادند.
- سه seed جایگزین در stage order اصلی overlap=34،33،34 از ۳۷ دادند.
- تغییر stage order با همان quota: UCO=29،OUC=37،OCU=36،CUO=28،COU=28؛ grid چهار seed × شش order overlap=25..37.
- stage order بخشی از algorithm است؛ scheduling بی‌اثر نیست. cutoffهای tie بزرگ و اثر node ID باید گزارش شوند.
- هیچ winner، historical parity، freeze تولیدی یا برتری علمی از این آمار نتیجه نشده است.
- selection هر پنج router در ممیزی امروز recompute شد و در JSON همراه این سند موجود است؛ source artifactها تغییر نکردند.

## ۱۴. experiment manifest، dedup و durable offline replay

`manifests/routing_experiment_draft_v1.json`: R0 control، R1-v2 و R2-v1 primary candidates؛ Semantic-v0 و R1-v1 optional ablation. DRAFT/NOT_AUTHORIZED_FOR_LIVE_EXECUTION بودن آن با authorization بعدی یک batch R0 یکسان نیست.

- هر arm ۳۷ blind و حداکثر ۳۷ conditional compare، حداکثر ۷۴ generation.
- سه primary arm جدا: حداکثر۲۲۲؛ union **۶۲ node و حداکثر۱۲۴ call**.
- comparison template هنوز identity واقعی نیست؛ actual blind response/class و digest لازم است.
- request identity بر complete canonical effective payload + execution context + dependency است؛ arm name حذف شده تا common-node request کاملاً برابر قابل reuse باشد؛ node ID، schema/prompt، settings و context باید برابر باشند.
- class برابر ولی raw blind متفاوت، comparison identity یکسان نمی‌سازد. تغییر provider/wire/context نیازمند identity تازه و authorization خودش است.
- اجرای synthetic قبلی: ۲۰۳ logical request، ۱۱۴ fixture dispatch، ۸۹ cache hit؛ R0=69،R1-v2=66،R2-v1=68 logical؛ reviewed/third-class accepted صفر.
- سپس journal durable opt-in اضافه شد؛ intent/UNCERTAIN قبل از fixture dispatch، completed قابل replay بدون dispatch؛ uncertain/rejected بدون retry. این **exactly-once delivery** را تضمین نمی‌کند.
- live dedup/authorization قرارداد جدا دارد؛ fixture را response واقعی provider جا نزنید.

## ۱۵. شش‌گرهٔ feasibility واقعی legacy؛ تاریخچهٔ کامل و immutable

ترتیب اصلی: **637,1243,130,682,2396,653**. original maximum۱۲ stage intent، ولی call count actual وابسته به abstention/failure است. پس از observation، continuationها با authorizationهای جدا و scopeهای مشخص ساخته شدند؛ اجازهٔ rerun عمومی ندارند.

| node/phase | outcome اصلی immutable | replay/diagnostic جدا | برداشت مجاز |
|---|---|---|---|
|637 blind، endpoint قدیمی|HTTP401 invalid_api_key|بدون تأیید billing|همان key طبق مالک قبلاً کار می‌کرد؛ user error اثبات نشد|
|637 blind، endpoint پنل، temp0.7|HTTP400 unsupported_value temperature|provider default1 را خواست|قدیم0.7 موفق بود، فعلاً سازگار نبود|
|637 blind، temp1|HTTP200؛ original ledger REJECTED، ثبت umbrella `INVALID_ENVELOPE_OR_USAGE`|separate identity/L1 diagnostic: PASS و abstain|revision difference در بررسی قبلی مطرح شد؛ umbrella اصلی را بازنویسی نکنید|
|1243 blind|HTTP200، REJECTED، L1_QUOTE_NOT_FOUND|PASS پس از wrapper amendment، non-abstain|original outcome هنوز FAIL است|
|1243 compare|HTTP200، REJECTED، L1_QUOTE_NOT_FOUND|دو quote مستقلاً non-exact|اصلاح parser/L1 برای passکردن توجیه نشد|
|130 blind|HTTP200، REJECTED، RETURNED_MODEL_MISMATCH|exact alias policy corrected، L1 PASS، non-abstain|blind تکرار نشد|
|130 compare|HTTP200، REJECTED، L1_QUOTE_NOT_FOUND|یک quote exact، دیگری فقط first-letter case mismatch|case-sensitive L1 درست عمل کرد|
|682 blind|HTTP200، COMPLETED، L1 PASS|non-abstain؛ سه quote exact|هیچ comparison در blind-only amendment انجام نشد|
|2396 blind|HTTP200، COMPLETED، L1 PASS|abstain=true|comparison مجاز نبود|
|653 blind|HTTP200، REJECTED، L1_QUOTE_NOT_FOUND|از دو quote یکی exact، دیگری first-letter case mismatch|بدون relaxation یا retry|

closeout موجود: **۶/۶ blind پاسخ HTTP200 و JSON parseable**، **۲/۶ original COMPLETED**، **۵/۶ current-rule L1 PASS شامل reassessmentها**، **۲/۶ blind abstention**، **۳/۶ non-abstaining L1-valid برای review**. **دو comparison attempted، هر دو original FAIL**؛ paired protocol کامل نشده است.

هشت HTTP200 phase response پایلوت (شش blind + دو compare) در closeout:

- input=8020، output=1562، reasoning=1089 (جزئی از output)؛ total input+output=9582.
- estimate با نرخ اعلامی مالک **USD0.001583**؛ نه invoice تأییدشده. دو HTTP rejection اولیه در این هشت response نیستند و billing آن‌ها UNKNOWN است.
- آخرین blind-only سه node به‌تنهایی: سه call، L1 PASS2/3، abstain1/3، input2983/output803/reasoning629، estimateUSD0.0006998.
- هیچ accepted training label از verifier یا L2 semantic approval حاصل نشده است.

root-cause auditهای مستقل decode/raw parser/source hash/Unicode/field/truncation را بررسی کردند؛ برای failureهای comparison defectی در parser، request construction یا validator یافت نشد. quote semantics ممکن است قابل‌فهم باشد ولی protocol exact-match را برآورده نکند. دو comparisonِ شرطی کوچک، population error rate یا systemic causal proof نیستند.

## ۱۶. endpoint، model identity، reasoning، privacy و cost

- تاریخی: `https://api.gapapi.com/v1/chat/completions`، `gpt-6-luna`، temperature0.7، n1؛ سه درخواست مستقل برای node/arm؛ explicit reasoning control در evidence بازیابی‌شده دیده نشد. absent parameter یعنی default نامعلوم، نه reasoning disabled.
- پنل فعلی مالک endpoint `https://api.gapgpt.app/v1` را توصیه کرد؛ callها به `/chat/completions` رفتند.
- wire feasibility مجاز بعدی: **temperature1، n1، max_tokens512، reasoning_effort omitted**؛ تغییر0.7→1 explicitly versioned/approved شد، scientific message legacy محفوظ ماند.
- exact identity policy فعلی دو رشته را در scope مجاز می‌پذیرد: **`gpt-6-luna` و `gpt-6-luna-2026-09-22`**. prefix، تاریخ دلخواه، cross-provider یا alias نامعلوم مجاز نیست.
- mapping یک **owner execution-contract policy** و fieldِ provider-reported است؛ اثبات مستقل equivalence upstream model نیست.
- revision-only restriction قبلی exact requested alias را ناخواسته کنار گذاشته بود؛ اصلاح minimal versioned با positive/negative tests شد؛ receipts گذشته upgrade نشدند.
- local reservationهای USD0.10 پایلوت، provider billing cap نبودند؛ هر scope approval خودش را داشت.
- نرخ‌های provisional مالک **USD0.10/M input و USD0.50/M output** هستند؛ current provider invoice/tariff/retention مستقلاً verify نشده‌اند. cached/cache-write و reasoning billing باید صریح باقی بمانند.
- successful HTTP200 تضمین قبول‌شدن JSON، L1، semantic support یا کافی‌بودن output cap نیست.
- API key در pilot CLI env یا hidden getpass بود؛ bridge batch جدید **فقط env `GAPGPT_API_KEY`** می‌گیرد، نه hidden fallback. این تفاوت باید به کاربر توضیح داده شود.

## ۱۷. مراحل جدید منطق که از بررسی فایل‌ها کشف شد

این‌ها پس از commit قدیمی `3b1ad8c` انجام شده‌اند و در خلاصهٔ قدیمی این چت نبودند:

| commit | تغییر واقعی | مرز علمی |
|---|---|---|
|389af3b|Rich Prompt V2 opt-in؛ EVERY quote exact|اصلاح prompt prospective، نه دستکاری seal|
|492427d + 8cb17ff|crash-durable synthetic journal و SQLite cleanup|بدون paid call، بدون auto retry uncertain|
|1700cd9|`precomparison_l2_gate=True` checkpoint|blind L1 non-abstain در L2_PENDING_BEFORE_COMPARISON متوقف می‌شود؛ evaluator خودکار نیست|
|ad576e0|automatic concordance screen opt-in|semantic judge/L2 نیست|
|58dddb8|قرنطینهٔ proposal و experimental GCN plan admission|public PROPOSE آموزش‌پذیر نیست؛ adapter جدا فقط plan|
|387573a|یک CLI برای authentic Cora140 Rich V2 synthetic runner|real responses نیستند|
|a1b8444|public CI جدا از private pilot tests|skip را PASS حساب نمی‌کند|
|f1c4d80|GapGPT gateway bridge، fake/live، ledger و cost reserve|live به approval دقیق نیاز دارد|
|eee2cb8 + 5628b00|exact approval/wire/budget tests و safe diagnostics|pricing/retention به‌دروغ verified نمی‌شوند|
|d273652|scoped owner authorization با evidence flags false|owner consent با provider verification فرق دارد|
|66521fe|contract جدا4096 پس از reasoning-only truncation|wire amendment، نه reset درخواست قبلی|
|0b375ea|authorization دقیق Cora140/R0/37/74/.40 برای4096|فقط hash pairهای معین؛ اجازهٔ cohort/router/model دلخواه نیست|
|2373b96|read-only L1 rejection diagnostic بدون body disclosure|همان batch halted باقی است|

## ۱۸. منطق دقیق Automatic Concordance و GCN admission

نسخه: **`sara.arbitration.automated_concordance.v1`**؛ opt-in experimental/unvalidated، default legacy عوض نشده است. با precomparison human checkpoint هم‌زمان فعال نمی‌شود.

پس از دو response L1-valid و audit readback:

- abstain، invalid provenance/class، third-class یا اختلاف blind/compare رد/abstain می‌شوند.
- counter-evidence غیرخالی، auxiliary warning یا uncertainty صریح veto می‌شوند.
- primary_topic دو phase پس از strip/casefold باید یکسان باشد؛ این lexical consistency است، **semantic equivalence نیست**.
- حداقل یک supporting target quote مشترک exact بین دو phase لازم است.
- class پیشنهادی باید یکی از candidateهای frozen باشد؛ confidence همان candidate historical است، calibrated verifier confidence نیست.
- screen داخلی ممکن است action=ACCEPT بدهد، ولی pipeline خروجی routed را **PROPOSE، accepted=false و training_class_index=null** می‌کند؛ L2=NOT_ASSESSED و semantic_validation=NOT_PERFORMED.
- تکرار همان quote نامربوط در دو stage ممکن است از screen عبور کند؛ این مشکل semantic با concordance حل نشده است. دو stage هم independent model نیستند.

نسخهٔ adapter: **`sara.gcn.experimental_concordance_admission.v1`** در `downstream/prospective.py`، با report hash و frozen-pair hash مستقل و version صریح. selection، candidate eligibility، totals و no-third-class را دوباره بررسی می‌کند و فقط matched plan می‌سازد. **فقط offline report با provider_calls=0** را می‌پذیرد؛ live report برای training admission پذیرفته نیست. digest محاسبه‌شده در همان call، جای approval علمی مستقل را نمی‌گیرد.

## ۱۹. نتیجهٔ واقعی synthetic runner و fake HTTP؛ نه علمی

artifactهای موجود به‌طور read-only تأیید شدند:

| اجرا | blind/compare COMPLETED | dispatch اول | replay بعدی | baseline retained | routed proposal | معنای نتیجه |
|---|---:|---:|---:|---:|---:|---|
|Rich V2 synthetic روی authentic140/R0|37/37|74 fixture|0 dispatch +74 hit|93|5|فقط integration/Resume؛ potential98/140=70%|
|GapGPT fake HTTP envelope|37/37|74 fake|0 dispatch +74 hit|93|5|wire/usage/accounting fixture؛ provider cost واقعی صفر|

fake envelope usage و dollar estimate، مصنوعی‌اند و billing واقعی نیستند. plan-only output موجود است؛ GCN train نشده است. مسیرها `.local_artifacts/sara3_rich_runner` و `.local_artifacts/sara3_gapgpt_fake_v1` هستند.

## ۲۰. اجرای واقعی جدید Cora140/R0، ابتدا512 سپس4096

این آزمایش **cohort140 با37 routed** است، نه اجرای کل140 node با verifier و نه ادامهٔ seal شش‌گرهی legacy. prompt=Rich V2، response=rich_evidence.v1، automatic concordance V1، L2 NOT_ASSESSED.

### batch اول512

- `.local_artifacts/sara3_gapgpt_live_cora140_r0_20261105`.
- یک blind dispatch؛ HTTP200، nonfinal/truncated (`TRUNCATED_OR_NONFINAL`)؛ ledger REJECTED، صفر COMPLETED.
- envelope گزارش می‌کند input1522، output512 و reasoning512؛ output budget صرف reasoning شده و rich JSON کامل تولید نشده است.
- summary موجود فقط usageِ completedها را جمع می‌کند، بنابراین usage=0 در آن **صفر billing نیست**. read-only envelope estimate: **USD0.0004082** با نرخ اعلامی؛ invoice UNKNOWN.
- original ledger/receipt محفوظ است؛ cap4096 در contract جدا و authorization جدا تغییر کرد.

### batch دوم4096؛ آخرین وضعیت قابل اثبات

- `.local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105`.
- fixed model/endpoint، temperature1/n1، max_input_tokens32768، max_tokens4096، timeout120؛ maximum74 calls و USD0.40 declared local aggregate.
- hash context: `c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8`.
- hash gateway contract: `59fd3de634a4aabae97fc9df02c396c5c435819e8b7f4cdbde1fe7837a8c165f`.
- **۵۳ actual intent/response**: ۲۹ blind COMPLETED +۲۳ compare COMPLETED +یک compare REJECTED؛ صفر uncertain. هر۵۳ request/wire/response/context binding و۱۰۹ content-addressed JSON receipt در journal در ممیزی حاضر بررسی شدند.
- ۵ blind abstention میان۲۹ blind معتبر و یک compare abstention میان۲۳ compare معتبر.
- node1814 compare: HTTP200، model alias مجاز، finish stop، JSON parseable؛ یک support و یک counter با **همان normalized exact quote**؛ reject `L1_DUPLICATE_EVIDENCE`، نه quote fabrication.
- ۵۲ response با قواعد فعلی دوباره L1 PASS گرفتند؛ rejected quote duplication نیز independently replay شد. اصل outcome عوض نشد.

### usage با denominator روشن

| محدوده | input | output | reasoning (داخل output) | estimate نرخ اعلامی USD |
|---|---:|---:|---:|---:|
|۵۲ COMPLETED؛ summary اصلی|79,337|32,297|در summary اصلی جدا جمع نشده|0.0240822|
|یک REJECTED node1814 compare؛ raw envelope|1,423|895|687|0.0005898|
|همه۵۳ response؛ ممیزی تازه|80,760|33,192|18,619|0.0246720|

invoice/charges واقعی verify نشده‌اند. محاسبهٔ جدید فقط **reported usage × user-declared rates** است؛ reasoning را دوباره روی output اضافه نکنید. local reserved upper در summary **USD0.2822144** برای۵۳ attempt است، نه میزان پول مصرف‌شده. سقف نظری۷۴ attempt4096 با همان نرخ‌ها **USD0.3940352** است و هنوز provider billing guarantee نیست.

returned model در۵۲ completed:۲۲ alias و۳۰ dated؛ با rejected مجموع۵۳:۲۳ alias و۳۰ dated. این‌ها provider-reported هستند.

### پوشش، proposal و ادامهٔ متوقف

- baseline retained93/140، provisional0؛ **صفر routed training label یا verified semantic correction**.
- در report، reasonهای routed: third-class diagnostic7، auxiliary warning5، blind abstention5، unresolved counter-evidence10، verifier abstained1، duplicate1 و هشت not-attempted که فعلاً کد timeout دارند.
- **۸ blind هنوز در همین Rich V2 batch dispatch نشده‌اند**: `2487,2396,2238,2317,2022,2379,2490,2534`.
- ممکن است بعضی از این IDs در پایلوت legacy response داشته باشند؛ این به معنی انجام Rich V2 request نیست. schema/prompt/context متفاوت است و reuse خودکار مشروع نیست.
- batch کامل یا original paired protocol complete نیست؛ هیچ scientific winner یا GCN improvement نمی‌توان نتیجه گرفت.

## ۲۱. ناهماهنگی‌های واقعی کشف‌شده در ممیزی انتقال

1. **State/README/registry قدیمی:** چند milestone هنوز NOT_DISPATCHED و no remote/NO real verifier نوشته‌اند. به‌جای rewrite تاریخ، یک latest factual snapshot و append outcome لازم است. docs مراحل قبلی باید historical بمانند.
2. **هشت not-attempted با reason timeout:** پس از halted شدن gateway، loop عمومی pipeline برای باقی‌مانده‌ها خطای `TIMEOUT_UNCERTAIN_NO_RETRY` ثبت کرده است. SQLite برای آن هشت node intent ندارد و UNCERTAIN=0 است؛ آن‌ها **timeout واقعی نیستند**. اصلاح کوچک reporting بعدی باید NOT_ATTEMPTED/HALTED_BEFORE_DISPATCH را از ambiguity واقعی جدا کند؛ transport/arbitration نیازمند relaxation نیستند.
3. **summary usage فقط completed:** excluded rejected call ممکن است usage/charge داشته باشد. ممیزی تازه آن را جدا محاسبه کرد؛ original summary/receipt عوض نشد. صفر summary اول512 را zero-cost معرفی نکنید.
4. **L1 duplicate support/counter:** یک شرط ساختاری فعلی است؛ به‌خودی‌خود semantic wrong class را ثابت نمی‌کند. تغییر احتمالی به policy/prompt نیازمند بررسی prospective و test است، نه silent dedup برای passکردن مشاهدهٔ جدید.
5. **دو human schema:** closeoutِ user از schema کوچک مستقل استفاده کرده است؛ چهار rubric dimension canonical را ندارد. اعتبارسنجی شش پاسخ آن مساوی import رسمی به `sara.l2.human_review.v1` یا Shadow نیست.
6. **authorization در کد تغییر کرده است:** bridge دیگر globally disabled صرف نیست؛ CLI با `--enable-real-dispatch` و hash-pinned scoped owner authorization می‌تواند live شود. provider flags false/unverified باقی می‌مانند. در چت بعدی اجرای عمومی runner را «حتماً offline» فرض نکنید.
7. **manual backup guide نام قدیمی دارد:** `docs/MANUAL_GITHUB_BACKUP.md` هنوز destination پیشنهادی `parand1khalili/llm-gnn-sara` را می‌گوید؛ remote فعلی **`https://github.com/Parand1khalili/LLM-GNN.git`** است. guide قدیمی را blindly اجرا نکنید و remote را تغییر ندهید.
8. **provenance manifestها snapshot هستند:** `implementation_lineage.json` و `drive_backup_plan.json` hashes مربوط به زمان ساخت را دارند؛ طبیعی است active source/docs بعداً تغییر کنند. آن‌ها را source immutable conflict با historical originalها اشتباه نگیرید. طرح backup قدیمی complete/current artifact backup نیست.
9. **untracked user utilities:** پنج script کاری در root وجود دارند؛ بخشی از closeout/human validation در آن‌هاست، نه Git history. پاک یا blanket-stage نشوند؛ محتوا پیش از versioning جدا review شود.
10. **regression قدیمی robustness با selector جدید هماهنگ نیست:** تست `test_five_selections_keep_actual_runtime_requests_and_conditional_protocol` هنوز `pipeline.route_r0` را patch می‌کند، اما production اکنون از `pipeline.select_router` استفاده می‌کند. بررسی مستقل نشان داد R0 همان ۶۱ fixture call را دارد، ولی تست برای Semantic انتظار ۶۴ دارد؛ injection به selector جدید نمی‌رسد. این failure به‌تنهایی اثبات خرابی router یا L1 نیست. اصلاح کوچک بعدی باید test injection را به public interface فعلی متصل کند و درخواست‌های common-node را واقعاً برای هر پنج selection بسنجد.
11. **SQLite connection lifetime در Windows:** تست diagnostic tampering هنگام cleanup با WinError32 روی `fixture_journal.sqlite` خطا داد. هم helper تشخیصی و هم همان تست از `with sqlite3.connect(...)` بدون explicit close استفاده می‌کنند؛ context manager تراکنش را مدیریت می‌کند و الزاماً connection را نمی‌بندد. کوچک‌ترین بررسی/اصلاح بعدی استفاده از `contextlib.closing` و regression خطای binding/tampering است. در این درخواست هیچ اتصال historical بازنویسی یا production patch اعمال نشد.

هیچ production logic، historical receipt یا seal برای «اصلاح» این اختلاف‌ها در این درخواست تغییر داده نشده است.

## ۲۲. downstream GCN آماده‌شده و کار واقعاً انجام‌نشده

- CE/noPS مقایسهٔ primary ساده؛ WCE/noPS supplementary انتخاب‌شدهٔ قبلی.
- Cora2708، selected140؛ Primary135 و Sensitivity140؛ test2568 ثابت complement کامل140 است. excluded/abstained node به test منتقل نمی‌شود.
- دو layer، hidden64، dropout0.5، ReLU، بدون batchnorm؛ Adam lr0.01/wd0.0005؛۳۰epoch، last checkpoint، no validation/early stopping؛ seeds0..9 matched.
- feature L2 normalization و frozen min-max confidence weights؛ constant confidence→ones؛ WCE برابر `mean(CE_i*w_i)` است، نه تقسیم بر sum weights.
- کلاس GCN تاریخی reviewed reuse شده و forward مصنوعی۴-node قبلاً PASS شده؛ training optimizer روی دادهٔ واقعی اجرا نشده است.
- runtime و training-label construction از GT جدا هستند. evaluation API از runtime جداست.
- adapter experimental فعلی live report را نمی‌پذیرد؛ قبل از controlled live-label GCN به contract admission جدا، freeze، approval training و ارزیابی مستقل نیاز است.
- هیچ عدد دقت جدید SARA/GCN، اثر causal یا generalization در این recovery تأیید نشده است.

## ۲۳. GraphScope و environment

GraphScope در `web/graphscope` static React/TypeScript/Cytoscape atlas است؛ شش بخش، research evidence478node/525edge،280annotation،8condition/160savedfit، و full topology2708/5278. export آن historical snapshot است؛ live private SARA responses یا human judgments به آن اضافه نشده‌اند. جملهٔ NO_REAL_VERIFIER_RESULT در export، محدودیت همان export است، نه نفی اجراهای بعدی.

نسخه‌های ثبت‌شده: Node24.22.1،pnpm11.25.0،React19.2.0،Vite7.3.7،TypeScript5.9.3،Cytoscape3.33.1. milestone قدیمی build/browser QA و advisory audit ثبت شده؛ ممیزی حاضر۱۴ JS test و TypeScript noEmit را دوباره اجرا کرد، بدون network یا deployment. existence یک workflow manual Pages اثبات deployment نیست.

offline package dependency اجباری third-party ندارد؛ optional CPU محیط ثبت‌شده Python3.12.14/Torch2.15.0+cpu/PyG2.7.0/NumPy2.3.5/tiktoken0.14.0 است. historical successful receipt: Python3.13.16/Torch2.11.0+cpu/NumPy2.1.3/PyG2.7.0. این‌ها یک environment نیستند؛ فایل‌های `configs/offline_tested_environment.json` و `configs/historical_successful_environment.json` را جدا بخوانید. در recovery initial TLS issuer error با trust roots معتبر حل شد؛ TLS verification خاموش نشد. environment.yml/startup تاریخی را blindly اجرا نکنید.

## ۲۴. tests و integrity checks ممیزی حاضر

گزارش دقیقِ نتیجهٔ regression نهایی در `reports/PROJECT_HANDOFF_AUDIT_2026-11-05.json` ثبت شده است؛ اعداد test قدیمی را نتیجهٔ امروز ننامید.

موارد بالفعل بررسی‌شده:

- root/branch/HEAD/log/remote configuration و tracked/untracked status.
- هر۲۵ recovered source hash؛۹ pinned input و۱۴۰ node alignment؛۲۸۰ frozen vote equivalence؛historical P0.
-۳۱ member outer seal و۱۳ member nested seal، با manifest hashهای اصلی.
-۵۳ wire/raw/context binding در live4096 ویک wire/raw/context binding در live512؛۱۱۴ content-addressed journal JSON مجموع دوbatch.
-۵۲ L1-valid rich response replay ویک duplicate rejection replay؛هیچ semantic judge اجرا نشد.
- structural validation شش completed closeout review وaggregateهای self-attested؛بدون انتشار پاسخ‌ها.
- syntax parse هر۷۱ Python source در package وپنج user utility بدون اجرای CLIهای نویسنده.
-۱۴/۱۴ GraphScope JavaScript test وTypeScript `tsc --noEmit` PASS.

اولین full Python suite در sandbox:۴۱۵ test run،صفر assertion failure ولی۴۱۹ error ثبت شد؛عمدتاً Windows ACL/AUDIT_UNAVAILABLE وcleanup permission. تعداد error می‌تواند از test بیشتر باشد چون setup وcleanup جدا ثبت می‌شوند. این اجرا PASS نیست. بازاجرای محلی با network guard وdenial روی actual human directories جدا ثبت شده است؛audit ACL را برای عبور tests ضعیف نکردیم.

**نتیجهٔ نهایی full guarded local suite: ۴۲۲ تست، ۴۱۸ PASS، یک FAIL، یک ERROR و دو SKIP در 207.344 ثانیه.** FAIL مربوط به obsolete selector patch در robustness است؛ ERROR مربوط به SQLite cleanup lock در diagnostic tampering. دو skip: تست POSIX permission روی Windows، و filesystem symlink به‌دلیل نداشتن مجوز؛ ZIP symlink rejection جدا تست می‌شود. بنابراین وضعیت امروز **FULL_REGRESSION_NOT_GREEN** است. پیام‌های «Canary/Batch blocked» در خروجی suite از negative mock tests بودند؛ هیچ dispatch واقعی در این تست‌ها رخ نداد.

log محلی: `C:\Users\Admin\AppData\Local\Temp\sara_handoff_regression_local_20261105.txt`. برای گزارش assertion و traceback کامل به همین log مراجعه کنید. هیچ‌یک از failures برای سبزکردن گزارش مخفی یا skip نشده‌اند.

مرز review: این بررسی evidence-oriented وscope-wide است؛اثبات خط‌به‌خط امنیت/درستی تمام کد،ارزیابی معنایی،بازخوانی تمام۱۸۰ weight،live provider verification یاremote backup audit نیست.

## ۲۵. Git وbackup امروز

remote فعلی درlocal config: `https://github.com/Parand1khalili/LLM-GNN.git`، نه upstream CurryTang. هنگام شروع ممیزی HEAD وlocal tracking `origin/main` هر دو `2373b9685b195080d81f3fcecd88001a9b04a8ff` بودند؛tracked diff/staged diff خالی بود. **tracking equality بدون network اثبات SHA فعلی remote یاPrivate visibility نیست**. در این درخواست fetch/ls-remote/push انجام نشد.

پنج فایل untracked پیشین محفوظ ماندند:

```text
closeout_sara3_feasibility.py
diagnose_closeout_readiness_v2.py
diagnose_gapgpt_post130.py
diagnose_sara3_closeout_readonly.py
verify_human_l2_readonly.py
```

این handoff وJSON audit جدید نیزlocal وuncommitted هستند تا مالک آن‌ها را مرور/منتقل کند. commit خودکار انجام نشد. برایcode backup مستقل هنوزremote readback لازم است؛Drive backup جدید درmanifest فقطPLANNED_NOT_UPLOADED وdestination unapproved است. وجودlocal `.local_artifacts`،sync folder یاorigin tracking،backup مستقل نیست.

دانلود credentials یا انتشار عمومی private reviewer directory ممنوع است. برای چت بعدی این سند و JSON aggregate و در صورت نیاز code/docs غیرحساس را بدهید؛ کل `.local_artifacts` را در چت عمومی یا Git نریزید.

## ۲۶. کارهای باقی‌مانده؛ اولویت وapproval روشن

### اولویت ۱: ثبت صادقانهٔ وضع موجود، بدون API

1. این handoff و actual ledgerها نقطهٔ شروع باشند؛ inventory/reconstructionهای موفق را از صفر تکرار نکنید.
2. latest state/registry را با snapshot واقعی update کنید، به‌صورت append و بدون تغییر historical outcomes.
3. در reporting، هشت node بدون intent را NOT_ATTEMPTED_AFTER_HALT بنامید، نه timeout واقعی؛ focused regression بنویسید. این کوچک‌ترین defect روشن گزارشگری است.
4. هزینهٔ completed، rejected با usage و unknown billing را جدا گزارش کنید؛ اصل receiptها عوض نشوند.
5. node1814 duplicate support/counter را read-only از جهت contract تفسیر کنید. خودکار dedup، L1 relaxation یا claim wrong class نکنید.
6. دو مشکل regression تازهٔ این ممیزی را با تغییر محدود و بدون اثر بر historical artifact بررسی کنید: شمارش call در robustness fixture و بسته‌نشدن SQLite در diagnostics روی Windows. این‌ها در این درخواست اصلاح نشده‌اند.

### اولویت ۲: review علمی خروجی‌های واقعی موجود، بدون inference تازه

7. سه pair واقعی closeout و disagreementها را با provenance صادقانه جمع‌بندی کنید؛ canonical چهاربُعدی و schema کوچک closeout را جدا نگه دارید. human answers را تغییر ندهید.
8. برای genuine Rich V2 outputها review مستقل و blinded تعریف کنید؛ consensus قدیمی یا LLM judge جای آن نیست. quote معتبر اما claim نامربوط، مسئلهٔ اصلی L2 است.
9. اگر recordها به Shadow/canonical وارد شوند، adapter/version صریح و binding کامل داشته باشند؛ از روی agreement یا self-attestation، gold نسازید.

### اولویت ۳: تصمیم prospective دربارهٔ ادامه، بدون retry بی‌مجوز

10. دربارهٔ بستن batch ناتمام یا amendment بعدی تصمیم علمی بگیرید؛ نتیجهٔ جزئی و مشروط به sample selection را گزارش کنید.
11. هر revised prompt، L1 duplicate policy یا output budget، contract نسخه‌دار و comparison/control مناسب می‌خواهد. original sealed legacy، P0 و receiptها تغییر نکنند.
12. هر ادامهٔ live به scope/request list/context/hash، privacy/spending approval و no-redispatch check تازه نیاز دارد؛ این handoff چنین مجوزی نداده است.
13. R1-v2/R2-v1 در آزمایش واقعی matched با R0 هنوز ارزیابی نشده‌اند؛ آمار coverage و HH، winner تعیین نمی‌کند.

### اولویت ۴: پایان‌نامه، downstream و recovery

14. یک plan علمی matched با CE/noPS primary و WCE/noPS supplementary ثبت کنید؛ coverage، class retention، abstention و هزینهٔ واقعی روشن باشند. live-label admission از offline fixture adapter جداست.
15. فقط با مجوز جدا GCN training/evaluation اجرا شود؛ نشت GT و test tuning ممنوع. canonical features/graph conversion قابل‌اعتماد و environment سازگار لازم است.
16. raw ZIP و admission هشتصد‌وچهل‌تایی برای raw historical reproducibility را از مسیر Colab تکمیل کنید؛ برای ادامهٔ کد offline، مانع قدیمی را خودسرانه برنگردانید.
17. جزئیات missing Judge002/Policy002/P1 wire را از original artifact، اگر هست، بازیابی کنید؛ وگرنه MISSING_EVIDENCE حفظ شود. equivalence بدون شاهد نسازید.
18. proposal ablationها، dataset/holdout واقعاً untouched، budget/retention/privacy و نتایج matched downstream هنوز ناتمام‌اند. Cora/CiteSeer قبلاً development بوده‌اند.
19. پنج utility untracked و private artifactهای مهم را از نظر حفظ، نسخه‌بندی و backup مرور کنید. manual GitHub push و Drive artifact backup با readback مستقل انجام شوند؛ private judgment/response در Git نرود.
20. limitations، negative outcomeها، protocol amendmentهای پس از مشاهده، seed variability در مقابل LLM replicate و عدم head-to-head با paper در تز صریح ثبت شوند.

## ۲۷. نقشهٔ فایل‌ها و اجرای امن چت بعدی

همهٔ مسیرهای زیر نسبت به ریشهٔ واقعی بالا هستند:

| موضوع | فایل‌ها |
|---|---|
| قواعد/وضع/تاریخچه | AGENTS.md، PROJECT_STATE.md، EXPERIMENT_REGISTRY.jsonl، README.md |
| evidence recovery | manifests/recovered_sources.json،frozen_artifacts.json،authentic_inputs.json،implementation_lineage.json |
| raw recovery | manifests/raw_response_requirements.json،unresolved_raw_responses.json؛scripts/colab_recover_responses.py،verify_intake.py |
| frozen IO/vote/PS | src/llmgnn_sara/io/{frozen,project,evidence}.py؛annotation/{voting,replay,prompts,_narrative_v0}.py؛filtering/ps.py |
| routes | sara2/policy.py؛sara3/{atlas,r1_candidate,r1_coverage,r2_candidate,selection}.py |
| runtime/L1/rich/audit | sara3/{pipeline,evidence,rich_evidence,inputs,audit,ledger}.py |
| offline routing experiment | manifests/routing_experiment_draft_v1.json؛sara3/{experiment,experiment_cache,durable_fixture}.py؛evaluation/routing_experiment.py |
| L2 | evaluation/{l2_benchmark,l2_reviews,l2_shadow}.py؛configs/l2_development_benchmark.json؛docs/L2_*.md |
| rich / automatic / new runner | sara3/{automated_policy,durable_rich,runner}.py؛ docs/AUTOMATED_ARBITRATION_V1.md، SARA3_RICH_RUNNER.md |
| current live bridge | sara3/{gapgpt_live,gateway_run,gateway_preflight,gateway_diagnostics}.py؛ configs/gapgpt_rich_v2*_proposed.json |
| historical pilot | pilot/{protocol,ledger,readiness,identity,canary,remaining_gapgpt,outstanding_gapgpt}.py و CLI wrapperهای جدا |
| P0 | manifests/historical_p0.json؛pilot/historical_p0.py؛docs/HISTORICAL_P0_ARM_CONTRACTS.md |
| GCN | downstream/{plan,model,frozen,prospective}.py؛evaluation/metrics.py |
| UI/topology | web/graphscope/README.md،VERIFICATION.md،TOPOLOGY_RECOVERY.md؛public/data/*.json |

فقط diagnostic خواندنی زیر همان batch موجود را می‌خواند؛ نه key می‌خواهد، نه call جدید می‌زند:

```powershell
Set-Location -LiteralPath 'C:\Users\Admin\Documents\ChatGPT\llm-gnn'
.venv\Scripts\python.exe -B -m llmgnn_sara.sara3.gateway_diagnostics `
  --output-root .local_artifacts/sara3_gapgpt_live_cora140_r0_4096_20261105 `
  --expected-context-sha256 c41b7a6ecec46a2a99c3b570f7e0b093756db4db98d692f4bb956135584599f8
```

فرمان‌های canary/remaining/outstanding/four/post130/blind-only قدیمی را اجرا نکنید؛ scopeهایشان شروع‌شده و terminal هستند. فرمان `runner --mode live` را هم برای «دیدن وضعیت» اجرا نکنید؛ ممکن است با credential/approval دقیق هزینه کند. برای node جدید یا output root جدید صرفاً به‌منظور دورزدن ledger مجوزی وجود ندارد.

### متن پیشنهادی برای آغاز چت جدید

> ابتدا این handoff و JSON ممیزی آن، AGENTS.md و HEAD فعلی را بخوان. inventory را از صفر شروع نکن. وضع قدیمی PROJECT_STATE.md را وضعیت امروز فرض نکن. روی main بمان و user untrackedها و حریم private human/raw audit را محفوظ نگه دار. آخرین batch Rich V2/4096 در node1814 comparison با L1_DUPLICATE_EVIDENCE بعد از 53 attempt متوقف است؛ هیچ retry/live/GCN/GT/push مجاز نیست. ابتدا state/reporting را از ledgerها reconcile کن؛ not-attempted را با timeout یکی نگیر، original outcome را از diagnostic reclassification جدا کن و بعد کوچک‌ترین offline تغییر را پیشنهاد بده. دو regression حل‌نشدهٔ این ممیزی را از گزارش tests بخوان. داوری خودکار فعلی semantic L2 نیست؛ proposalها quarantined و training labels null هستند. شش review جدید closeout سه pair خوداظهاری‌شده‌اند و با شش consensus development قدیمی فرق دارند. بدون مجوز جدا، هزینه، protocol، L1 یا training admission را تغییر نده.

## ۲۸. محدودیت این handoff

این متن با حافظهٔ چت و سورس/رسیدهای واقعی موجود تکمیل شد. کار انجام‌شده در چت دیگر با file/commit/receipt به‌عنوان evidence تأیید شد، نه با حدس. تاریخ mtime به‌تنهایی scientific completion نیست. در این نشست API، network، GT، training، push، Drive write یا ویرایش historical artifact انجام نشد. فرم‌های unfinished جلسهٔ قدیمی L2 و submissionهای consensus قدیمی باز نشدند. برای جزئیات اجرای regression به JSON همراه مراجعه کنید.

تاریخچهٔ کامل commitهای main و نتیجهٔ نهایی checks در پیوست آمده است.


## پیوست الف: تاریخچهٔ کامل commitهای main تا snapshot این سند

این log از Git محلی خوانده شد؛ وجود commit به معنی اجرای live، صحت علمی یا backup مستقل نیست.

```text
b0249a8 | 2026-10-29 | Preserve exact recovery intake and enforce manual pushes
ee6dd5c | 2026-10-29 | Add pinned Colab raw recovery and offline ZIP admission
c3a4e00 | 2026-10-30 | Reconstruct and verify the integrated offline SARA pipeline
cf06266 | 2026-10-30 | Record offline reconstruction evidence and backup readiness
e8cb583 | 2026-10-30 | Add SARA recovery documents and pilot preparation
3e56105 | 2026-10-30 | Integrate authentic Cora evidence and seal offline SARA pilot
7886603 | 2026-10-30 | Build GraphScope v2 static research atlas with pinned evidence
b28d3b2 | 2026-10-30 | Separate research evidence and gated full Cora topology views
573b1e4 | 2026-10-30 | Recover exact Cora topology without unpickling and admit full graph
628aa64 | 2026-10-31 | Restore historical P0 selection manifest with pinned offline validation
803234d | 2026-10-31 | Specify historical P0 arm contracts and unresolved evidence gates
6f8fe0c | 2026-10-31 | Enforce L1 evidence checks and fail-closed V1 arbitration with private audit
661d800 | 2026-10-31 | Add authentic SARA-3 boundary replay with deterministic synthetic fixtures
84900e9 | 2026-10-31 | Add opt-in rich evidence schema with L1 checks and private diagnostics
b34ef1f | 2026-10-31 | Add GT-free L2 rubric and illustrative development benchmark
f887c2e | 2026-10-31 | Add private blinded human L2 review collection and comparison workflow
e9ffdb6 | 2026-11-01 | Add versioned GT-free R1 candidate router and offline diagnostics
0264f93 | 2026-11-01 | Separate R1 observed risk from missing Atlas coverage
dc08852 | 2026-11-01 | Add prospective stratified R2 candidate router and offline comparisons
cbf70ff | 2026-11-01 | Review router seed and stage robustness with fixed verifier contracts
f61d11f | 2026-11-01 | Connect pinned draft router selections to offline verifier experiments
ad25b50 | 2026-11-01 | Complete offline pilot readiness ledger and parser recovery rehearsal
8b30ac5 | 2026-11-01 | Add private evaluation-only L2 shadow assessment intake and comparison
6b2f828 | 2026-11-01 | Define fixed-scope third-agent feasibility scientific protocol v1
dee4978 | 2026-11-01 | Document minimal provider preflight and unresolved gateway execution gates
efc2083 | 2026-11-01 | Fix GapGPT provider decision and narrow blind-canary preflight blockers
383a6ad | 2026-11-01 | Prepare owner-confirmed single GapGPT blind canary with secure key input
bbcf934 | 2026-11-01 | Prepare separate account-panel GapGPT canary without altering failed intent
a982331 | 2026-11-01 | Prepare explicit temperature1 canary for observed GapGPT parameter rejection
ec47109 | 2026-11-01 | Diagnose returned model revision mismatch and preserve provider usage
6929462 | 2026-11-01 | Add owner-approved sequential GapGPT feasibility continuation
27e0bff | 2026-11-01 | Amend L1 matching for single decorative double-quote wrappers
5f35bd1 | 2026-11-02 | Add bound outstanding-only pilot continuation after L1 amendment
076a18e | 2026-11-02 | Scope remaining feasibility execution to four never-attempted nodes
7ed0ccc | 2026-11-02 | Restore approved exact model alias in versioned post130 execution contract
3b1ad8c | 2026-11-02 | Add explicit three-node blind-only feasibility amendment
389af3b | 2026-11-03 | Add opt-in rich SARA-3 prompt v2 with offline integration tests
492427d | 2026-11-03 | Add crash-durable offline fixture journal and safe replay tests
8cb17ff | 2026-11-03 | Close SQLite connection in corrupted receipt regression test
1700cd9 | 2026-11-03 | Add opt-in L2 checkpoint before prospective verifier comparison
ad576e0 | 2026-11-03 | Add opt-in prospective automatic concordance arbitration with audit-backed decisions
58dddb8 | 2026-11-03 | Quarantine SARA-3 proposals and add pinned experimental GCN plan admission
387573a | 2026-11-04 | Add durable Rich V2 synthetic SARA-3 runner with resumable audited fixtures
a1b8444 | 2026-11-04 | Separate public regression from sealed private GapGPT fixture checks
f1c4d80 | 2026-11-05 | Add fail-closed GapGPT Rich V2 gateway bridge with fake HTTP and durable cost reservations
eee2cb8 | 2026-11-05 | Test exact Gateway batch approval and reject changed pricing or routing
5628b00 | 2026-11-05 | Add exact GapGPT wire and budget preflight with audit-safe response diagnostics
d273652 | 2026-11-05 | Honor scoped SARA-3 batch authorization without falsifying provider tariff verification
66521fe | 2026-11-05 | Prepare isolated GapGPT 4096-token amendment after reasoning-only truncation
0b375ea | 2026-11-05 | Authorize exact Cora140 GapGPT 4096-token amended batch on main
2373b96 | 2026-11-05 | Add read-only private GapGPT L1 rejection diagnostics without response disclosure
```

## پیوست ب: selected IDs فعلی هر router؛ فقط diagnostics

### r0

```text
637, 1243, 130, 682, 722, 734, 351, 2487, 2396, 1528, 653, 695, 267, 1283, 2238, 2317, 2022, 27, 207, 357, 1559, 568, 1120, 2379, 1814, 614, 917, 1751, 1649, 25, 1690, 2490, 2534, 114, 94, 1269, 552
```

### semantic

```text
682, 2396, 637, 1243, 130, 653, 267, 1120, 722, 917, 1751, 734, 25, 351, 2487, 94, 2291, 881, 2319, 181, 81, 2177, 2287, 1649, 1240, 979, 1946, 1764, 47, 1528, 695, 1283, 2238, 2317, 2022, 27, 207
```

### r1_v1

```text
351, 637, 734, 722, 160, 207, 267, 295, 375, 430, 552, 682, 743, 783, 862, 932, 1013, 1031, 1066, 1120, 1269, 1283, 1308, 1776, 1814, 1951, 1958, 2291, 2317, 2327, 2396, 2434, 2490, 2534, 2685, 2698, 130
```

### r1_v2

```text
722, 267, 682, 1120, 2291, 2396, 130, 1243, 653, 2319, 2487, 25, 47, 62, 972, 979, 1240, 1260, 1649, 1719, 1764, 1946, 2425, 2695, 81, 90, 94, 181, 436, 568, 614, 698, 711, 785, 881, 917, 1226
```

### r2_v1

```text
1013, 1958, 1283, 1031, 722, 267, 682, 1120, 2291, 2396, 130, 1243, 653, 2319, 2487, 25, 47, 62, 972, 979, 1240, 637, 734, 351, 1528, 695, 2238, 2317, 2022, 27, 207, 357, 1559, 568, 2379, 1814, 614
```

ترتیب این فهرست‌ها، order خروجی selector است؛ runtime عمومی بر ترتیب cohort پیمایش می‌کند. hash/context و dependency، تعیین‌کنندهٔ request identity هستند. این فهرست‌ها مجوز API جدید نیستند.


## پیوست ج: نتایج پیش از FeatProp از سند تاریخی موجود در Downloads

در ادامهٔ ممیزی، سند `C:\Users\Admin\Downloads\SARA_LLMGNN_Research_Results_2026-10-29_FA.md` نیز واقعاً پیدا و بخش‌های نتایج آن خوانده شد. بنابراین عبارت «این سند شخصاً در دسترس نبود» در یادداشت قدیمی SCIENTIFIC_PROTOCOL.md، محدودیت همان زمان است. اعداد این پیوست **secondary historical evidence** هستند؛ وزن‌ها، training و GT مربوط به این مطالعات در ممیزی حاضر بازاجرا/بازارزیابی نشدند. با جدول اصلی FeatProp ادغام نشوند.

### M1؛ Cora / PageRank2 / یک‌جهشی

| روش | GCN noPS (%) | GCN PS (%) |
|---|---:|---:|
| B1 | 68.13 | 71.05 |
| Raw3 | 67.94 | 70.43 |
| Rep1 | 67.87 | 70.69 |
| 1-hop Consensus | 69.50 | 70.90 |

برداشت تاریخی: Consensus در noPS بهتر بود، اما پس از PS از B1 بالاتر نبود. این با ادعای «context همیشه بهتر است» سازگار نیست.

### M2؛ Agreement تاریخی Cora، جدا از Agreement جدید FeatProp

- Agreement+PS: 69.57%.
- Agreement-only با ۱۲۷ target retained و noPS: 70.28%؛ نسبت به B1 noPS مرحلهٔ M1 حدود +2.15pp.
- Agreement+WCE: 70.02%.
- طراحی post-hoc بود؛ اثر علّی صرف توافق از این آمار جداگانه ثابت نشده است.

### M3؛ CiteSeer

| روش | GCN mean (%) |
|---|---:|
| B1 text-only | 64.818 |
| 1-hop Consensus | 64.123 |
| Agreement-only | 64.927 |

تفاوت Agreement با B1 فقط +0.109pp گزارش شد. اختلاف نسخهٔ raw/fixed دادهٔ CiteSeer در گزارش تاریخی ثبت شده؛ این یک compatibility risk است. canonical GTِ evaluator-only هرگز نباید وارد runtime شود. هیچ raw/fixed label در این ممیزی خوانده یا decode نشد.

### M4-A-R1؛ مقایسهٔ H2 و Uniform در مسیرهای 2-hop

| Dataset / روش | raw annotation صحیحِ گزارش‌شده | Brier گزارش‌شده |
|---|---:|---:|
| Cora H2 | 95/140 | 0.185175 |
| Cora Uniform | 95/140 | 0.181383 |
| CiteSeer H2 | 89/120 | 0.083778 |
| CiteSeer Uniform | 91/120 | 0.078851 |

| Dataset | H2 GCN mean ± SD (%) | Uniform mean ± SD (%) | delta pp |
|---|---:|---:|---:|
| Cora | 68.9836 ± 0.1682 | 69.4237 ± 0.2029 | +0.4400 |
| CiteSeer | 61.7221 ± 0.4532 | 64.0150 ± 0.3301 | +2.2929 |
| Macro دو dataset | 65.3529 | 66.7193 | +1.36646 |

این ۴۰ fit تاریخی از ۱۶۰ fit اصلی FeatProp جدا هستند. Uniform2Path3 را random walk معرفی نکنید؛ تصمیم ادامهٔ پروژه بازاجرای پرهزینهٔ همهٔ M1–M4 نبود.

### پنج prompt روی selection تاریخی PageRank2

| روش | raw correct گزارش‌شده از140 | درصد |
|---|---:|---:|
| B1 | 89 | 63.5714 |
| Consensus | 91 | 65.0000 |
| Narrative v0 | 96 | 68.5714 |
| Narrative v1 | 92 | 65.7143 |
| Narrative v2 | 91 | 65.0000 |

GCNهای تاریخی همان مطالعه: B1=64.96495±0.45146%، Narrative v0=70.63084±0.20443%، Narrative v1=69.17445±0.25128%. این setup، همان matched FeatProp جدید نیست؛ به‌عنوان تکرار مستقل آن ادعا نشود.

### Agreement-only جدید FeatProp؛ بیست fit مستقل از جدول160fit

| cohort | retained | Agreement mean ± SD (%) | delta مقابل B1+CE/noPS | delta مقابل v0+CE/noPS |
|---|---:|---:|---:|---:|
| Primary |126|71.211059±0.446395|+1.530374pp|+0.257009pp|
| Sensitivity |131|71.569315±0.428862|+1.725078pp|−0.163551pp|

در Primary، هفت seed بهتر و سه بدتر از v0؛ در Sensitivity، سه بهتر، شش بدتر و یکی برابر گزارش شده است. توافق همیشه بهترین downstream filter نیست. مجموع اصلی FeatProp160 + Agreement20 برابر180fit است و شامل M1–M4 نمی‌شود.

### اعداد مقاله؛ فقط published comparator

| روش مقاله | Cora mean ± SD (%) | CiteSeer mean ± SD (%) |
|---|---:|---:|
| FeatProp |72.82±0.08|66.61±0.55|
| FeatProp-W |73.56±0.13|68.04±0.69|
| PS-FeatProp |75.54±0.34|69.06±0.32|
| PS-FeatProp-W |76.23±0.07|68.64±0.71|

این جدول گزارش مقاله است، نه training ما یا baseline matched بازتولیدشده. اختلاف split، model، selection، prompt و protocol مانع head-to-head بدون مطالعهٔ کنترل‌شده است.
