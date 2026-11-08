# آزمایش افزایش واژگان Class Atlas

R1-v1 کاندیدای بازسازی‌شده است. ترتیب هر ۳۷ شناسهٔ پایه با بستهٔ Frozen آزمایش Expanded برابر بود. این تطابق انتخاب روی همین داده است؛ هم‌ارزی با کد گمشدهٔ Codex اثبات نشده است. دقت 74.3769% متعلق به GCN تاریخی Automated V1 + R1 است.

واژگان افزوده، انتخاب مهندسی از مفاهیم فصول ۴، ۶ تا ۱۰ و ۱۳ [کتاب Mitchell](https://www.cs.cmu.edu/~tom/mlbook.html) و [Poole و Mackworth](https://artint.info/3e/html/ArtInt3e.html) هستند. قواعد انتخاب پیش از GT بسته شدند. تطابق با توکن انگلیسی کامل، بدون stemming؛ شمارش هر واژه حداکثر یک بار. همان تابع risk و همان tie-break شناسه اجرا شد.

|کلاس|قدیم|افزوده (اطلس جدید = مجموع دو ستون)|
|---|---|---|
|rule_learning|rule, rules, induction, logic|horn, clause, clauses, predicate, predicates, antecedent, consequent, foil|
|neural_networks|neural, network, networks, backpropagation|perceptron, multilayer, sigmoid, activation, neuron, neurons, recurrent, convolutional|
|case_based|case, cases, retrieval, analogy|analogical, exemplar, exemplars, instance, instances, adaptation, similarity, nearest|
|genetic_algorithms|genetic, evolutionary, mutation, crossover|chromosome, chromosomes, fitness, population, populations, recombination, genotype, offspring|
|theory|theorem, bound, bounds, complexity|pac, learnability, vc, hypothesis, hypotheses, generalization, convergence, shattering|
|reinforcement_learning|reward, policy, reinforcement, markov|rewards, policies, temporal, bellman, action, actions, exploration, exploitation|
|probabilistic_methods|bayesian, probabilistic, probability, likelihood|bayes, posterior, prior, conditional, marginal, inference, marginalization, priors|

Freeze خصوصی 6b624adac49e9a8e3a78de6d7628e4fc1b654b21b5307a33ebd9b5ef4a007fe0

اشتراک 27؛ فقط قدیم 10؛ فقط جدید 10.

|نسخه|بدون Match در ۱۴۰ / منتخب|خطای B1 / Narrative / حداقل یکی در ۳۷|توزیع کلاس پیش‌بینی B1 / Narrative در منتخبان (به ترتیب اطلس)|
|---|---|---|---|
|expanded|18 / 18|[26, 21, 27]|[3, 1, 2, 0, 22, 2, 7] / [3, 4, 1, 0, 22, 1, 6]|
|old|30 / 30|[23, 20, 24]|[2, 4, 4, 0, 19, 0, 8] / [2, 7, 3, 0, 18, 0, 7]|

expanded: Atlas SHA-256 b9ebe1f8dfbe3223a1698b7fd487bfcad255ea61071cc72b4dc9e44e86ef1b68؛ انتخاب مرتب 97954cb2920d9480d33484dff1287d3fcbf36dd0367a277b6a1eafe9692df4ee

توزیع Risk (امتیاز، تعداد) در کل و منتخبان:
[('0', 40), ('1/15', 1), ('1/12', 4), ('1/9', 10), ('2/15', 2), ('1/6', 12), ('1/5', 1), ('2/9', 2), ('1/4', 2), ('1/3', 36), ('1/2', 4), ('8/15', 1), ('19/30', 1), ('2/3', 20), ('5/6', 2), ('1', 2)]
[('1/3', 7), ('1/2', 4), ('8/15', 1), ('19/30', 1), ('2/3', 20), ('5/6', 2), ('1', 2)]

old: Atlas SHA-256 6979189ef981956f3f1dc00e3bd0d10c1ffdc3bd9584a477380dd469a823ee3f؛ انتخاب مرتب 2dc4241989d50759abbb04232e8fbebc2200f741144f6917d60957cdd7095b1f

توزیع Risk (امتیاز، تعداد) در کل و منتخبان:
[('0', 49), ('1/12', 1), ('1/9', 3), ('1/6', 8), ('2/9', 2), ('1/4', 1), ('1/3', 35), ('1/2', 3), ('7/12', 2), ('2/3', 32), ('5/6', 1), ('1', 3)]
[('7/12', 1), ('2/3', 32), ('5/6', 1), ('1', 3)]

افزایش Match می‌تواند از کلمات چندمعنا یا اشاره به روش کمکی ناشی شود. تعداد خطاهای انتخاب‌شده یک تشخیص پسینی روی همین cohort است؛ اختلاف انتخاب‌ها زوجی است و انتخاب واژگان بعدی براساس همین خطاها خطر بیش‌برازش دارد.

مرحله دوم BLOCKED_PENDING_APPROVAL است. نخست درخواست‌های مشترک را با هویت کامل، context و وابستگی Blind تطبیق دهید. برای فازهای فاقد پاسخ معتبر مجوز هزینه و ارسال خصوصی لازم است. برای هر بردار آموزشی تازه Admission مستقل و برای Fit تازه مجوز Training لازم است. در این مرحله فراخوانی مدل و آموزش صفر بود.

LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT
