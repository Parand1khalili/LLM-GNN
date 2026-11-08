# مطالعهٔ پسینی Homophily و خطاهای SARA-3

همسایگی مستقیم پس از حذف Self-loop و یکتاسازی و اجتماع دو جهت سنجیده شد. برچسب همسایه فقط در این Evaluator خوانده شد. مرزها پیش از خواندن GT ثبت شدند؛ h<0.5 heterophilic، h=0.5 mixed و h>0.5 homophilic. نود منزوی undefined است.

Protocol SHA 62c93b11937c36dfbcb3b69ec56117699010a9d33a47a9bf290c02f66eb21557

Result SHA abba9e433029c7c9a5138cb9d35e0a270ff8640dd97b65a89f326a4a0f4616c6

|گروه|N|میانگین h|میانه h|میانگین Degree|
|---|---:|---:|---:|---:|
|both_correct|95|0.9061287250760935|1.0|5.08421052631579|
|both_wrong|38|0.8214912280701754|1.0|4.2368421052631575|
|only_b1_wrong|6|0.8333333333333334|1.0|2.3333333333333335|
|only_narrative_wrong|1|0.0|0.0|3|
|r0_selected|37|0.8229086229086229|1.0|3.7567567567567566|
|r0_unselected|103|0.8917599660318107|1.0|5.067961165048544|
|r1_v1_selected|37|0.7968468468468468|1.0|3.5945945945945947|
|r1_v1_unselected|103|0.9011219632578856|1.0|5.12621359223301|
|expanded_selected|37|0.8175675675675675|1.0|3.4864864864864864|
|expanded_unselected|103|0.8936785975620927|1.0|5.165048543689321|
|B1_correct|96|0.8966898841898842|1.0|5.0625|
|B1_wrong|44|0.8231060606060606|1.0|3.977272727272727|
|B1_abstain|0|None|None|None|
|Narrative_correct|101|0.9018042463587018|1.0|4.920792079207921|
|Narrative_wrong|39|0.8004273504273505|1.0|4.205128205128205|
|Narrative_abstain|0|None|None|None|
|C_correct|72|0.9248914665581333|1.0|4.833333333333333|
|C_wrong|21|0.8317460317460318|1.0|4.809523809523809|
|C_abstain|47|0.8136179423413465|1.0|4.51063829787234|
|Expanded_V1_correct|67|0.9230176954057551|1.0|5.044776119402985|
|Expanded_V1_wrong|12|0.7680555555555556|0.9|4.75|
|Expanded_V1_abstain|61|0.8400007096728408|1.0|4.360655737704918|
|V1_Relaxed_correct|69|0.9180026897418202|1.0|5|
|V1_Relaxed_wrong|15|0.8144444444444444|1.0|5.4|
|V1_Relaxed_abstain|56|0.8346436301793445|1.0|4.196428571428571|
|agent_blind_correct|16|0.875|1.0|2.75|
|agent_blind_wrong|12|0.6875|1.0|4.583333333333333|
|agent_compare_correct|14|0.8035714285714286|1.0|2.5714285714285716|
|agent_compare_wrong|9|0.75|1.0|5.444444444444445|
|fusion_removed_errors|24|0.78125|1.0|3.2083333333333335|
|fusion_retained_errors|21|0.8317460317460318|1.0|4.809523809523809|
|third_correct|2|0.75|0.75|3.5|
|third_wrong|3|1.0|1.0|8|

## تفسیر و آزمایش آینده

مقایسهٔ Degree-conditioned توصیفی است. گروه‌های کوچک و نودهای دارای همسایهٔ مشترک مستقل نیستند؛ آزمون معنی‌داری یا ادعای علّی انجام نشد. H=0.5 مرز قراردادی است و بهینه نشده است.

Detection، تولید کلاس، پذیرش و GCN چهار خروجی جدا دارند. V1-Relaxed پنج امتناع را به دو درست و سه غلط تبدیل کرد؛ صحت Quote یا توافق دو فاز، تأیید معنایی نیست. از پنج نتیجه قاعدهٔ جدیدی ساخته نشد.

برای آزمون بعدی، روی CiteSeer با دسترسی و پروتکل مستقل، واژگان/Policy و بودجه را پیشاپیش ثبت کنید؛ کنترل بدون Agent با Mask برابر و کلاس‌های Baseline لازم است. ارزیابی متن و شواهد روی Development مستقل از Test، پیش‌نیاز طراحی گیت معنایی است. هزینه و مجوز API/Training باید جدا تعیین شود.

جزئیات پنج پیشنهاد و Ground Truth فقط در Artifact خصوصی با ACL مالک نگهداری شدند. هیچ بهبود GCN اندازه‌گیری نشده است. LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT


## تفاوت پنج پیشنهاد

|ویژگی|دو پیشنهاد درست|سه پیشنهاد غلط|
|---|---:|---:|
|Mean Homophily|0.75|1.0|
|Mean Degree|3.5|8|
|Counter-evidence present|1|3|
|Auxiliary warning|2|3|
|Shared quote|2|1|
|Literal topic agreement|0|0|
|Explicit uncertainty|0|0|

وجود Warning هر دو گروه را دربرمی‌گیرد و Topic لفظی در هیچ مورد برابر نبود؛ این ویژگی‌ها روی پنج نود اعتبار مستقل ندارند. هیچ گیت جدیدی از این تفاوت‌ها ساخته نشد. سه پیشنهاد غلط با وجود h=1 رخ دادند؛ GT همسایگان نباید وارد Policy شود.

برای هر پنج پیشنهاد، متن و پاسخ دو فاز، L1، Counter-evidence، Confidence و Atlas hit count، طول متن، توزیع GT همسایه و علت رد V1 در Artifact خصوصی درج شد. دادهٔ inference و post-hoc در آن مشخص است.

نمودار میانگین reports/homophily_groups.svg و Histogram در reports/homophily_distribution.svg است. Histogram تجمیعی در reports/homophily_distribution.json ثبت شده است. هیچ فایل GraphScope تغییر نکرد.

آزمون‌های اجراشده:3 تست Homophily،5 تست Relaxed و4 تست Frozen Atlas همگی PASS شدند. Full Suite اجرا نشد.

فرمان Windows برای مطالعهٔ اصلی: .venv\Scripts\python.exe -B -m llmgnn_sara.evaluation.homophily
فرمان تست: .venv\Scripts\python.exe -B -m unittest discover -s tests -p test_homophily.py -v
