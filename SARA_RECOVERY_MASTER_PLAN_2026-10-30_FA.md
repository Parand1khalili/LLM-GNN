# برنامهٔ مرجع بازیابی و تحویل پژوهش LLM–GNN / SARA

**تاریخ ممیزی:** ۲۰۲۶-۱۰-۳۰  
**وضعیت:** طرح بازسازی مبتنی بر بررسی فقط‌خواندنی؛ نه اعلام بازیابی اجرایی کامل  
**قاعدهٔ تغییر:** تا تأیید موجودی، مسیر مخزن Git و گیت‌های مربوط، اجرای API پولی، آموزش مدل، نوشتن در آرشیو تاریخی یا Push مجاز نیست.

## ۱. هدف، محدوده و معیار خاتمه

هدف محصول: ساخت یک pipeline پژوهشی بازتولیدپذیر برای برچسب‌گذاری محدود گره‌ها با B1 text-only و Narrative v0، مسیریابی عدم‌قطعیت، داوری محدود SARA-3، optional abstention، و آموزش/ارزیابی GCN بر pseudo-labelها؛ همراه با شواهد قابل دفاع برای پایان‌نامه. **GCN مدل نهایی است؛ LLM تنها annotator/verifier است.**

خارج از محدودهٔ حیاتی فعلی: بازاجرای پرهزینهٔ همهٔ M1–M4، اضافه‌کردن مکرر روش‌های 2-hop/PPR/MMR، تغییر بی‌قاعدهٔ loss/PS و tuning بر اساس GT، ساخت داشبورد یا زیرساخت پیچیدهٔ غیرضروری.

**Definition of Done:** کد اجراشدنی از محیط تازه، تست‌های مستقل offline، ردیابی response→pseudo-label→GCN، مرز سخت GT، artifactهای frozen، اجرای محدود واقعی Agent سوم با مجوز، گزارش هزینه و کیفیت، مقایسهٔ matched با baseline، ارزیابی خارج از development در صورت امکان، و بازتولید یا توضیح مستند عدم‌بازتولید نتایج کلیدی. موفقیت عددی از پیش تضمین نمی‌شود؛ نتایج منفی نیز با طراحی صحیح قابل دفاع‌اند.

## ۲. یافته‌های مستقیم ممیزی ۳۰ اکتبر (نه ادعای اجرای تازه)

| دارایی | شواهد امروز | وضعیت دقیق |
|---|---|---|
| [ریشهٔ Drive پروژه](https://drive.google.com/drive/folders/1u9eLA8uZVJxZsLi38h1-eDPhNDwj92ML) | پوشه‌های `LLMGNN_reference`, `LLMGNN_data`, `api_runs`, `env_backup` و `startup.py` فهرست شدند | **موجودی مستقیم تأیید**؛ اجرای سالم هنوز UNKNOWN |
| [سورس pre-Codex](https://drive.google.com/drive/folders/1vn5sGNemegM25DnHkA_lrwFB_Hy7okVv) | `llm.py`, `main.py`, `helper`, `structure`, `openail` و اجزای اصلی قابل مشاهده‌اند | سورس قابل بازیابی است؛ تست runtime مستقل انجام نشده |
| [داده‌ها](https://drive.google.com/drive/folders/1zf2Sx1mtKYAQvHxW_dzNBUZUvyFbE6R3) | Cora، CiteSeer raw/fixed، فایل‌های OpenAI-cache، پوشهٔ `aax` و active | وجود فایل‌ها قطعی؛ برای `.pt` از بارگذاری غیرامن خودداری شود |
| FeatProp selection | `selection_manifest.json` واقعاً خوانده شد؛ SHA-256=`dc8260974c7c0ca2e828f2d069e2896e9bcf2c363b15ca81d9f09d2803c9b12c` | **Hash-matched** با گزارش تاریخی؛ ۱۴۰ target |
| Narrative source | `src/structure/narrative_topology_v0.py`، SHA-256=`6fbad422911ba0fc13c6b4df6235fadb68e9dac7b92221cb50c010aa7d07f3d1` | **Hash-matched** |
| 1-hop selector | `src/structure/selector.py`، SHA-256=`52be8f75854bf4f7208d82d4fac71954a0002146685c823a77508f2d7471c859` | **Hash-matched** |
| pseudo-labelهای frozen | B1 SHA-256=`c6bc236ac5f8c1615067a10750cb150ecaf54fbe458afd4df7e750f92ce4b141`؛ v0 SHA-256=`181806c4622449c8f9cdc9bdabb725232666fdc95394b3a8d7b78067b385ff02` | فایل‌های هر دو بازو واقعاً خوانده شدند؛ هر کدام ۱۴۰ شناسهٔ یکتا، ۳ sample برای هر target، صفر failure ثبت‌شده، و ترتیب target یکسان؛ صحت محاسبات علمی و تمام پاسخ‌های خام مستقل اثبات نشده |
| FeatProp downstream | `results.json` SHA-256=`c0da09960528dfdaafbb7a3289f724a7ad5e1d73d484a32f9dc16e55208f055b` و `freeze_receipt.json` SHA-256=`a6008c72b6fd74b2e42d90006e375f3ec3dfc2367a136c2f75e973aecd907eca` | **Hash-matched**؛ ۱۶۰ fit در گزارش ثبت شده، آموزش مجدد اجرا نشده |
| M4-A-R1 | `m4a_r1_downstream_gcn_results_canonical_gt.json` SHA-256=`ae6e7f677ea1db15975de730f0e1e561f819c263616e4c60c11888ce382dabf6` | **Hash-matched**؛ نتیجهٔ تاریخی، نه اجرای جدید |
| Agreement جدید | summary/receipt و پوشه‌های ۲۰ seed fit در Drive دیده شدند | گزارش تاریخی ۲۰ fit؛ بررسی استقلال اجرا لازم است |
| مدل‌های GCN | پوشه‌های متعدد seed، report، receipt و وزن‌ها در `experiments/matched_cora` موجودند | موجودی در سطح پوشه مستقیماً تأیید شد؛ گزارش ممیزی قبلی ۱۸۰ فایل وزن با بررسی Hash/CRC را ثبت کرده؛ در این نشست همهٔ وزن‌ها مستقل بازخوانی نشدند |
| [Colab اصلی](https://colab.research.google.com/drive/1VTFrVkixOMmnkXEGWprtE7m4rSWuqJsY) | JSON کامل خوانده شد: ۵۶۸ سلول، ۵۴۵ سلول کد و ۵۳۰ کد-سلول با خروجی؛ آخرین modified: ۲۰۲۶-۱۰-۲۹ | **موجود است؛ هیچ سلولی اجرا نشد.** در سورس سلول‌ها اشارهٔ صریح به پیاده‌سازی SARA-2/3 یافت نشد؛ ممکن است اسکریپت‌های جداگانه مربوط باشند |
| محیط | `env_backup/llmgnn_env.tar.gz` حدود ۳٫۹۶ GB، `requirements` و `environment.yml` موجود | وجود، نه تضمین سازگاری یا امن بودن اجرای مستقیم |
| `.git` | `.git` تاریخی داخل Drive دیده شد | این مخزن upstream مرجع است و اثبات private GitHub backup نیست؛ Git status/HEAD مستقل استخراج نشده |
| Codex-era SARA-2/E0/E1/SARA-3/P0/P1/P2 | در اسناد تاریخچه گزارش شده، اما روی `D:\SARA2` از بین رفته | **RECONSTRUCTION_REQUIRED** تا اثبات خلاف با کد واقعی؛ آخرین checkpoint executable بعد از خرابی `UNKNOWN` |

> **مرز اطمینان:** مشاهدهٔ فایل، Hash-match، receipt داخلی، سلامت مدل در forward، بازاجرای مستقل GCN و اعتبار علمی out-of-sample، پنج سطح متفاوت شواهد هستند. آن‌ها را در پایان‌نامه ادغام نکنید.

## ۳. وضعیت علمی مبنا

- مطالعهٔ FeatProp روی Cora: دو Prompt روی همان LLM، همان ۱۴۰ target و سه sample matched. B1 raw: ۹۶/۱۴۰؛ Narrative v0 raw: ۱۰۱/۱۴۰.
- در Sensitivity + WCE/noPS، B1=`70.595794 ± 0.344555%` و v0=`73.165888 ± 0.448564%`؛ اختلاف زوجی `+2.570093 ± 0.273141 pp`. طبق نتایج frozen، ۸/۸ pipeline و ۸۰/۸۰ seed-level difference مثبت‌اند؛ ۸۰ seed به معنی ۸۰ annotation مستقل نیست.
- Agreement-only FeatProp همیشه از v0 بهتر نبود. E0 تاریخی می‌گوید ۳۸ target هر دو غلط، ۳۶ مورد توافق بر همان کلاس غلط و ۲۱ HH هر دو غلط؛ این‌ها تحلیل اکتشافی **پس از GT** هستند.
- R0 تاریخی ۳۷ مورد را escalate و صفر HH را ارجاع می‌داد؛ R1 و R2 آفلاین با همان ظرفیت ۳۷ مورد، به‌ترتیب ۱۸ و ۷ HH را انتخاب می‌کردند. این آمار تنها **Routing Coverage** است، نه اثبات اصلاح label.
- SARA-3 P0/P1/P2 کد و تست آفلاین گزارش‌شده دارند، اما هیچ Live verification/GCN جدید تأییدشده ندارند. ۱۲ درخواست پایلوت برنامه‌ریزی شده‌اند؛ اجرای generation هنوز مجاز نیست.
- Cora و CiteSeer پیش‌تر development/diagnostics بوده‌اند. برای ادعای generalization، dataset یا split **واقعاً مستقل** باید قبل از دیدن GT و نتایج نهایی قفل شود. انتقال Atlas کلاس‌ها به dataset دیگر نیاز به طراحی از روی taxonomy عمومی، نه برچسب‌های گره‌ها دارد.
- عدد ۷۶٫۲۳٪ در مقالهٔ مرجع مربوط به setup آن مقاله است؛ مقایسهٔ مستقیم با ۷۳٫۱۶۶٪ محلی ادعای head-to-head نیست.

## ۴. تصمیم اجرایی: «اول حفظ، بعد replay، بعد Agent سوم»

**گیت A — Inventory/Seal (فقط خواندن):** فهرست recursive فایل‌ها با drive ID/size/hash، انتخاب یک Snapshot canonical pre-Codex، بررسی source provenance، بررسی خروجی خام و ۱۸۰ وزن، تعیین کنترل‌های missing. Freeze همهٔ artifactهای تاریخی. خروجی: `inventory.csv`، `evidence_matrix.md`، `recovery_gaps.md`. هیچ train/API.

**گیت B — کدبیس پیوسته و امن:** پس از تعیین existing branch و تأیید مسیر GitHub خصوصی توسط مالک، کپی read-only آرشیو را به workspace کد منتقل کنید؛ dependency lock مدرن اما با رفتار Frozen قابل replay؛ `AGENTS.md` کوتاه و اعمال‌شونده به تمام Codex sessions. هیچ Branch/PR جدید بدون دستور صریح؛ هیچ force push. source history را overwrite نکنید. خروجی: startup/checks reproducible.

**گیت C — Replay آفلاین FeatProp/Agreement:** ingest JSONهای B1/v0 و ۱۴۰ target؛ تست دقیق node-ID alignment، ۳ sample، class mapping، parser/voter و provenance؛ بازتولید post-filter و metric summary فقط از frozen data بدون LLM request. ثابت‌ماندن `data.y` بیرون runtime. اگر نیاز به آموزش GCN برای reproduction است، **مجوز جداگانه** بگیرید. خروجی: golden fixtures، replay reports و diff به baseline.

**گیت D — SARA-2 و E0/E1:** بازسازی Policy 002 و R0 فقط از specification غیر GT؛ تست آفلاین route count و confidence bucket. evaluator تشخیصی E0/E1 باید package و access جدا داشته باشد؛ هیچ GT outcome یا node-level diagnostic نباید وارد selector، prompt، Atlas یا router شود. نتایج E0/E1 historical exploratory برچسب بخورند.

**گیت E — SARA-3 MVP آفلاین:** Class Atlas با تعریف عمومی کلاس‌ها؛ Routerهای R0/R1/R2 با بودجه برابر؛ `Verifier` blind-first (بدون دیدن historical votes/confidence در فاز نخست)، سپس arbitration با مجوز کلاس سوم/abstain مشخص. V1 اجازهٔ پیشنهاد کلاس سوم دارد، ولی **نباید بدون آزمایش و Freeze آن را برای آموزش قبول کرد**. V2 آزمایشی و Live-blocked بماند. خروجی: wire schema، ۱۲ case fixed، deterministic dry-run، no-GT tests.

**گیت F — Live pilot (نیازمند approval جداگانه):** ابتدا hash/config/protocol و cost estimate، دسترسی provider و مالکیت حساب، token caps و safe logging را راستی‌آزمایی کنید؛ درخواست‌ها default-off باشند. برنامهٔ تاریخی ۱۲ call تنها یک **طرح** است. هر Generation، retry، سقف هزینه، تغییر مدل یا انتقال داده نیاز به مجوز معین دارد. timeout ناشناخته نباید duplicate request بسازد. خروجی: immutable ledger، exact responses، usage/cost، failure+abstain، frozen label set.

**گیت G — ارزیابی علمی:** مقایسهٔ matched و از پیش‌ثبت‌شدهٔ B1، v0، R0 و بهترین SARA-3 بر اساس `raw accuracy`, `coverage`, `precision/recall of corrections`, `abstention`, `tokens/$`, و مهم‌تر از همه `GCN downstream`. تفکیک `Primary/Sensitivity`, `noPS/PS`, `CE/WCE`, class distribution و paired seed؛ عدم نسبت‌دادن variability ده seed به عدم قطعیت LLM. استفاده از dataset مستقل در صورت فراهم‌شدن منابع و زمان؛ عدم tuning پس از بازکردن نتیجه. خروجی: جدول‌ها، محدودیت‌ها و متن پایان‌نامه همراه provenance.

## ۵. تقسیم کار عامل‌ها (در یک repo، بدون نوشتن هم‌زمان به فایل یکدیگر)

| عامل / نقش | مالکیت و خروجی | ممنوعیت / مرز |
|---|---|---|
| **Lead/Integrator** | نگهداشت acceptance criteria، plan freeze، تعیین existing branch، review و commit/push مجاز، اولویت‌های زمان | بدون مجوز Branch/PR نمی‌سازد؛ API/train و تغییر destructive نمی‌کند |
| **A — Recovery Forensics** | Inventory، Hash chain، source/dependency map، raw-output provenance؛ `recovery/` | فقط‌خواندنی در Drive؛ هیچ GT، API یا training |
| **B — Pipeline/GCN** | input adapters، parser/voter، cached replay، deterministic post-filter، GCN integration و fixtures؛ `src/core/`, `tests/core/` | به GT دسترسی ندارد؛ تغییر ماهیت Frozen بدون amendment ممنوع |
| **C — SARA Policy/Verifier** | Policy 002، Router R0/R1/R2، Atlas، blind verifier، arbitration، dry-run؛ `src/sara/`, `tests/sara/` | حق مشاهدهٔ E0 node-level/GT، tuning با outcomes یا Live call ندارد |
| **D — Independent Scientific QA** | در فضای محدود با دسترسی به GT فقط برای ارزیابی پس از Freeze؛ `evaluation/`, `reports/` | نتیجهٔ GT را به طراحی/قواعد اجرا بازنمی‌گرداند؛ نه تولید pseudo-label و نه training inputs |

قانون handoff: هر task یک artifact قابل demo، ورودی و خروجی contract، معیار پذیرش و test evidence دارد. فقط Lead تغییرات چند عامل را بعد از review و به‌صورت نوبتی روی **شاخهٔ موجودِ تعیین‌شده** ادغام می‌کند؛ هیچ Agent حق ساخت Branch/PR، push به upstream `CurryTang/LLMGNN` یا overwrite آرشیو Drive را ندارد.

## ۶. حداقل تست‌های Gate

- **Hash+provenance:** verify immutable selection, frozen prompt/response manifest, source hashes؛ پیدا کردن missing/orphan responses و consistency بین `original_fresh`, `historical_reuse`, `supplementary`.
- **Alignment:** ۱۴۰ شناسهٔ یکتا برای هر arm، global node IDs، ترتیب یکسان و label indices معتبر؛ برای CiteSeer تفاوت `raw_y`/`fixed_y` فقط در evaluator اعمال شود.
- **GT isolation:** runtime paths نمی‌توانند `data.y` یا diagnostics E0/E1 را وارد prompt، router، loss یا post-filter کنند؛ negative tests با inject کردن GT جعلی نباید تصمیم‌ها را تغییر دهد.
- **Prompt topology:** 1-hop واقعی، tie-break ثابت و جدا بودن A²X برای selection در مقابل SBERT برای context؛ تست length/token budget و fallback B1.
- **GCN:** seed matching، `model.train()` هر epoch، no early stopping مگر صریح در frozen protocol، test complement همسان؛ formula `mean(CE_i*w_i)` را بی‌سر و صدا به weighted mean دیگر تغییر ندهید.
- **Live safety:** default deny, idempotent ledger, no auto retry on uncertain state, explicit budget approval, masked secrets, frozen P0 case set, hash before submission.
- **Science:** تفکیک raw/downstream، dataset/selector/cohort، report mean±SD (جمعیت) و اختلاف زوجی؛ ثبت pre/post-GT design decisions؛ validation مستقل تنها روی دادهٔ untouched.

## ۷. برنامهٔ فشرده با گیت تحویل (پیشنهادی، نه زمان‌بندی تأییدشده)

| بازهٔ نسبی | تمرکز | شرط خروج |
|---|---|---|
| روزهای ۱–۳ | A + انتخاب existing repo/branch و امنیت backup | evidence matrix، inventory، دسترس‌پذیری منابع و گیت صفر |
| روزهای ۴–۷ | B/C: offline frozen replay و QA اولیه | parser/voter/test fixtures/GCN interface بدون درخواست پولی |
| روزهای ۸–۱۲ | D/E: SARA-2 و SARA-3 V1 offline | deterministic routing، blind verifier، ۱۲ wire-case آماده، no-GT audit |
| روزهای ۱۳–۱۷ | در صورت مجوز: token/cost preflight، ۱۲ call pilot و تحلیل | immutable outputs، بودجه/coverage و freeze results |
| روزهای ۱۸–۲۴ | matched GCN/validation مستقل در صورت مجوز و وقت | جداول اصلی و limitations، not-an-API-demo |
| روزهای ۲۵–۲۸ | نوشتن Method/Experiments/Results، بستهٔ دفاع و recovery dry-run | repo verified، evidence trail، گزارش و اسلاید دفاع |

**اگر زمان کمتر است:** ابتدا FeatProp+Narrative v0 بازتولیدپذیر و SARA-3 offline با آزمون و محدودیت روشن را تحویل دهید؛ آزمایش live و ادعای بهبود Agent سوم را مشروط و صادقانه گزارش کنید، نه اینکه نتیجهٔ synthetic را به‌جای measured جا بزنید. اگر آزمایش live اصلی پایان‌نامه است، از scope 2-hop و ablationهای غیرضروری کم کنید، نه از validation و GT separation.

## ۸. مسائل باز و تصمیم‌های لازم از مالک پروژه

۱. **تاریخ قطعی تحویل گزارش/دفاع** و نوع الزام استاد برای «Agent سوم live» در مقابل نمونهٔ تحقیقاتی قابل بازتولید.  
۲. مشخص‌کردن مسیر **مخزن Git و شاخهٔ موجود**؛ GitHub متصل در ممیزی فعلی مخزن خصوصی تأییدشدهٔ پژوهش نشان نداد، و `.git` در Drive متعلق به upstream است. برای ساخت private repo جدید باید صریحاً دستور داده شود.  
۳. بودجه و provider/model قابل دسترس امروز (نام تاریخی `gpt-6-luna` و gateway قدیمی الزاماً به معنای موجود بودن endpoint فعلی نیست)؛ تأیید امنیت/retention و مجوز جدا برای هر مرحلهٔ Live.  
۴. تعیین dataset/split مستقلِ واقعاً untouched و آستانهٔ علمی ازپیش‌تعریف‌شده برای go/no-go.  
۵. روش backup: private GitHub برای code و Drive برای artifact، با **readback+SHA** پس از انتقال.

## ۹. پیام آغازین پیشنهادی برای Codex (فقط audit، نه پیاده‌سازی)

```text
SARA RECOVERY / READ-ONLY GATE A
The old D:\\SARA2 Codex-era workspace is lost. Treat historical chats and P0/P1/P2 reports as reconstruction specifications, never as recovered executable code. The pre-Codex Google Drive archive and Colab notebook are our actual executable-artifact candidates.

First identify the actual existing local repository/workspace and current Git status/branch/remotes; DO NOT create a branch, PR, new repo, commit, or push. Do not assume that the upstream CurryTang/LLMGNN .git is our private project backup.

Read the linked Google Drive Prnd-project/LLMGNN_reference, LLMGNN_data, experiments/matched_cora, and the main Colab notebook. Inventory recursively, record file IDs, SHA-256, content class, and provenance. Verify B1/v0 frozen outputs, FeatProp selection, parser/voter, GCN run receipts/weights, and what actual source remains. Keep historical artifacts immutable. No GT access beyond the explicitly isolated evaluation context; do not use GT for policy/selection/annotation. Do not execute notebook cells, train a model, call LLM/API, modify Drive, or overwrite anything.

Deliver: (1) verified evidence matrix RECOVERED/HASH_MATCHED/CLAIM_ONLY/MISSING/UNKNOWN, (2) minimal build dependency map, (3) scientific and security gaps, (4) small prioritized vertical slices with offline acceptance tests. Stop for review before implementation. Preserve continuity on one user-selected EXISTING Git branch once authorized.
```

## ۱۰. اسناد مرجع

- پروپوزال `40131012_proposal.pdf` و مقالهٔ Chen et al., *Label-Free Node Classification on Graphs with Large Language Models (LLMs)*, ICLR 2024.
- `LLMGNN_project_history_2026-10-20_FA.md` (مرجع زمانی قدیمی‌تر، از گزارش ۲۹ اکتبر جدا).
- `LLMGNN_MEETING_REPORT_2026-10-24_FA.pdf` (نتایج تا ۲۴ اکتبر، نه اثبات SARA-3).
- `SARA_LLMGNN_Research_Results_2026-10-29_FA.md` (راهنمای سطوح شواهد و هدف SARA-3).
- `gpt-historychate.txt` و `Pasted markdown.md` (تاریخچهٔ تصمیم‌ها؛ **نه کد اجرایی**).

**هیچ فایل تاریخی بازنویسی نشد. هیچ notebook cell، API یا training اجرا نشد.**
