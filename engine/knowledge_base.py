"""
قاعدة المعرفة (Knowledge Base) لنظام شفاء AI.

تحتوي على:
  - SYMPTOMS     : الأعراض + مرادفاتها بالعامية المصرية والفصحى والإنجليزية + سؤال المتابعة
  - CONDITIONS   : الحالات المرضية البسيطة (Minor ailments) + احتمالات الأعراض لكل حالة
  - DRUGS        : الأدوية المتاحة بدون روشتة (OTC) + الجرعات + موانع الاستعمال
  - CHRONIC_MEDS : الأدوية المزمنة اللي ممكن المريض ياخدها (لفحص التداخلات)
  - INTERACTIONS : التداخلات الدوائية
  - RED_FLAGS    : علامات الخطر اللي تستوجب تحويل فوري للطوارئ

ملاحظة: الأرقام في LIKELIHOODS تقديرات تعليمية مبنية على الكتب المرجعية
(Symptoms in the Pharmacy - Blenkinsopp, Minor Illness or Major Disease - Nathan)
وليست مستخرجة من دراسة إحصائية، والغرض منها توضيح فكرة الاستدلال الاحتمالي.
"""

# ---------------------------------------------------------------------------
# 1) الأعراض
# ---------------------------------------------------------------------------
# كل عرض: name (الاسم بالعربي)، question (سؤال المتابعة)، synonyms (كلمات يتعرف بيها)
SYMPTOMS = {
    "fever": {
        "name": "حرارة / سخونية",
        "question": "هل عندك سخونية أو حرارة (أكتر من 38 درجة)؟",
        "synonyms": ["سخونيه", "سخونة", "سخن", "حراره", "الحمى", "عندي حمى", "درجة حرارتي", "fever", "temperature", "feverish"],
    },
    "high_fever": {
        "name": "حرارة عالية فجأة (39 أو أكتر)",
        "question": "هل الحرارة جت فجأة وكانت عالية (39 درجة أو أكتر)؟",
        "synonyms": ["حراره عاليه", "سخونيه جامده", "سخونيه عاليه", "حراره جامده", "high fever"],
    },
    "chills": {
        "name": "رعشة / قشعريرة",
        "question": "هل بتحس برعشة أو قشعريرة؟",
        "synonyms": ["رعشه", "قشعريره", "بردان", "سقعان", "chills", "shivering"],
    },
    "body_aches": {
        "name": "تكسير وآلام في الجسم والعضلات",
        "question": "هل عندك تكسير أو وجع في جسمك وعضلاتك؟",
        "synonyms": ["تكسير", "جسمي مكسر", "وجع في جسمي", "الام العضلات", "الم العضلات", "body ache", "body aches", "muscle pain", "myalgia"],
    },
    "fatigue": {
        "name": "إرهاق وتعب عام",
        "question": "هل حاسس بإرهاق أو تعب شديد؟",
        "synonyms": ["ارهاق", "تعبان", "خمول", "مرهق", "هبوط", "fatigue", "tired", "exhausted"],
    },
    "headache": {
        "name": "صداع",
        "question": "هل عندك صداع؟",
        "synonyms": ["صداع", "راسي بتوجعني", "دماغي بتوجعني", "وجع في راسي", "وجع راس", "headache", "head ache"],
    },
    "one_sided_headache": {
        "name": "صداع نابض في ناحية واحدة من الراس",
        "question": "هل الصداع بيكون نابض (بيدق) وفي ناحية واحدة من راسك؟",
        "synonyms": ["صداع نصفي", "نص راسي", "ناحيه واحده", "بيدق", "نابض", "شقيقه", "migraine", "throbbing", "one side"],
    },
    "photophobia": {
        "name": "حساسية من النور والصوت",
        "question": "هل النور أو الصوت العالي بيضايقك وبيزود الصداع؟",
        "synonyms": ["النور بيضايقني", "حساسيه من النور", "الضوء", "الدوشه بتضايقني", "photophobia", "light sensitivity"],
    },
    "band_headache": {
        "name": "صداع ضاغط زي الرباط حوالين الراس",
        "question": "هل الصداع إحساسه ضاغط زي رباط حوالين راسك أو في الجبهة والرقبة؟",
        "synonyms": ["رباط", "ضاغط", "ضغط على راسي", "زي الطوق", "tight band", "pressure headache"],
    },
    "stress": {
        "name": "ضغط نفسي أو قلة نوم",
        "question": "هل عندك ضغط نفسي أو توتر أو قلة نوم الأيام دي؟",
        "synonyms": ["توتر", "ضغط نفسي", "ضغط شغل", "قلق", "مش بنام", "قله نوم", "سهر", "مذاكره", "stress", "anxiety", "no sleep"],
    },
    "runny_nose": {
        "name": "رشح وسيلان من الأنف",
        "question": "هل عندك رشح أو مناخيرك بتنقط؟",
        "synonyms": ["رشح", "سيلان", "مناخيري بتنقط", "انفي بينزل", "runny nose", "rhinorrhea"],
    },
    "nasal_congestion": {
        "name": "انسداد الأنف (زكام)",
        "question": "هل مناخيرك مسدودة؟",
        "synonyms": ["زكام", "مناخيري مسدوده", "انفي مسدود", "مناخيري مقفوله", "انسداد", "انفي مقفول", "مزكم", "congestion", "blocked nose", "stuffy nose"],
    },
    "sneezing": {
        "name": "عطس متكرر",
        "question": "هل بتعطس كتير؟",
        "synonyms": ["عطس", "بعطس", "عطاس", "sneeze", "sneezing"],
    },
    "itchy_eyes_nose": {
        "name": "هرش في العين أو الأنف",
        "question": "هل عينك أو مناخيرك بتاكلك (هرش)؟",
        "synonyms": ["عيني بتاكلني", "هرش في عيني", "حكه في العين", "مناخيري بتاكلني", "itchy eyes", "itchy nose"],
    },
    "seasonal_trigger": {
        "name": "الأعراض بتزيد مع التراب أو تغيير الجو",
        "question": "هل الأعراض بتزيد مع التراب أو الغبار أو تغيير الفصول أو حيوانات أليفة؟",
        "synonyms": ["التراب", "الغبار", "تغيير الجو", "الربيع", "حساسيه", "حساسيتي", "dust", "pollen", "allergy", "allergic"],
    },
    "sore_throat": {
        "name": "التهاب أو وجع في الزور",
        "question": "هل زورك بيوجعك أو بتحس بألم وانت بتبلع؟",
        "synonyms": ["زوري", "الزور", "احتقان", "التهاب الحلق", "وجع في البلع", "بلعومي", "sore throat", "throat pain"],
    },
    "swollen_tonsils": {
        "name": "تضخم اللوز مع نقط بيضا",
        "question": "هل في تضخم في اللوز أو نقط بيضا عليها؟",
        "synonyms": ["اللوز", "اللوزتين", "نقط بيضا", "صديد في الزور", "tonsils", "white patches"],
    },
    "cough_dry": {
        "name": "كحة ناشفة",
        "question": "هل عندك كحة ناشفة (من غير بلغم)؟",
        "synonyms": ["كحه ناشفه", "سعال جاف", "كحه جافه", "dry cough"],
    },
    "cough_productive": {
        "name": "كحة ببلغم",
        "question": "هل عندك كحة ببلغم؟",
        "synonyms": ["بلغم", "كحه ببلغم", "سعال ببلغم", "productive cough", "phlegm", "sputum"],
    },
    "cough": {
        "name": "كحة",
        "question": "هل عندك كحة؟",
        "synonyms": ["كحه", "بكح", "سعال", "cough", "coughing"],
    },
    "chest_tightness": {
        "name": "تقل خفيف في الصدر مع الكحة",
        "question": "هل بتحس بتقل خفيف أو كتمة بسيطة في صدرك مع الكحة؟",
        "synonyms": ["تقل في صدري", "صدري تقيل", "chest heaviness"],
    },
    "loss_smell": {
        "name": "فقدان حاسة الشم أو التذوق",
        "question": "هل فقدت حاسة الشم أو التذوق؟",
        "synonyms": ["مش بشم", "فقدان الشم", "مش بدوق", "فقدان التذوق", "loss of smell", "anosmia"],
    },
    "diarrhea": {
        "name": "إسهال",
        "question": "هل عندك إسهال (براز سايل أكتر من 3 مرات في اليوم)؟",
        "synonyms": ["اسهال", "بطني سايبه", "اسهل", "اسهلت", "diarrhea", "diarrhoea", "loose stool"],
    },
    "nausea": {
        "name": "غثيان",
        "question": "هل عندك غثيان أو لعيان نفس؟",
        "synonyms": ["غثيان", "لعيان نفس", "نفسي غامه", "قرفان", "nausea", "nauseous"],
    },
    "vomiting": {
        "name": "ترجيع / قيء",
        "question": "هل بترجّع (قيء)؟",
        "synonyms": ["ترجيع", "برجع", "رجعت", "قيء", "استفراغ", "vomit", "vomiting", "throwing up"],
    },
    "abdominal_cramps": {
        "name": "مغص وتقلصات في البطن",
        "question": "هل عندك مغص أو تقلصات في بطنك؟",
        "synonyms": ["مغص", "تقلصات", "بطني بتوجعني", "وجع في بطني", "الم البطن", "cramps", "abdominal pain", "stomach ache"],
    },
    "food_trigger": {
        "name": "أكل من بره أو أكل مشكوك فيه قبل الأعراض",
        "question": "هل أكلت أكل من بره أو أكل مشكوك فيه قبل ما الأعراض تبدأ؟",
        "synonyms": ["اكلت من بره", "اكل بايظ", "اكل مسمم", "تسمم", "food poisoning", "street food"],
    },
    "constipation": {
        "name": "إمساك",
        "question": "هل عندك إمساك (بتدخل الحمام أقل من 3 مرات في الأسبوع أو بصعوبة)؟",
        "synonyms": ["امساك", "ممسوك", "مش بدخل الحمام", "constipation", "constipated"],
    },
    "hard_stool": {
        "name": "براز ناشف وصعوبة في الإخراج",
        "question": "هل البراز ناشف وبتحتاج تضغط جامد عشان تخرج؟",
        "synonyms": ["براز ناشف", "صعوبه في الاخراج", "بزق", "hard stool", "straining"],
    },
    "bloating": {
        "name": "انتفاخ وغازات",
        "question": "هل عندك انتفاخ أو غازات؟",
        "synonyms": ["انتفاخ", "غازات", "بطني منفوخه", "bloating", "gas", "flatulence"],
    },
    "low_fiber": {
        "name": "قلة أكل الخضار والمية",
        "question": "هل بتشرب مية قليلة أو مش بتاكل خضار وفاكهة كفاية؟",
        "synonyms": ["مش بشرب مايه", "مش باكل خضار", "low fiber", "low water"],
    },
    "heartburn": {
        "name": "حموضة وحرقان في الصدر",
        "question": "هل عندك حموضة أو حرقان طالع من المعدة للصدر؟",
        "synonyms": ["حموضه", "حرقان في صدري", "حرقان في المعده", "حرقه", "heartburn", "acidity"],
    },
    "regurgitation": {
        "name": "ارتجاع وطعم مر في البق",
        "question": "هل بتحس بأكل أو طعم مر/حامض راجع لبقك؟",
        "synonyms": ["ارتجاع", "طعم مر", "طعم حامض", "بيطلع لبقي", "reflux", "regurgitation"],
    },
    "worse_lying": {
        "name": "الأعراض بتزيد بعد الأكل أو مع النوم",
        "question": "هل الأعراض بتزيد بعد الأكل التقيل أو لما تنام على ضهرك؟",
        "synonyms": ["بعد الاكل", "لما انام", "after meals", "lying down"],
    },
    "epigastric_pain": {
        "name": "ألم في فم المعدة",
        "question": "هل عندك ألم في فم المعدة (أعلى البطن)؟",
        "synonyms": ["فم المعده", "وجع في معدتي", "معدتي بتوجعني", "epigastric", "stomach pain"],
    },
    "dysuria": {
        "name": "حرقان أو ألم مع البول",
        "question": "هل عندك حرقان أو ألم وانت بتعمل حمام (بول)؟",
        "synonyms": ["حرقان في البول", "حرقان وانا بعمل حمام", "الم مع البول", "dysuria", "burning urination"],
    },
    "urinary_frequency": {
        "name": "كثرة التبول",
        "question": "هل بتدخل الحمام (بول) كتير وعلى فترات قريبة؟",
        "synonyms": ["كتره التبول", "بدخل الحمام كتير", "بتبول كتير", "frequency", "frequent urination"],
    },
    "lower_abdominal_pain": {
        "name": "ألم أسفل البطن",
        "question": "هل عندك ألم أسفل البطن (تحت السرة)؟",
        "synonyms": ["تحت السره", "اسفل البطن", "تحت بطني", "lower abdominal pain", "suprapubic"],
    },
    "menstrual_pain": {
        "name": "ألم مرتبط بالدورة الشهرية",
        "question": "هل الألم مرتبط بميعاد الدورة الشهرية؟",
        "synonyms": ["الدوره", "مغص الدوره", "البيريود", "period", "menstrual", "dysmenorrhea"],
    },
    "itchy_rash": {
        "name": "هرش وطفح جلدي",
        "question": "هل عندك هرش أو طفح في الجلد؟",
        "synonyms": ["هرش", "حكه", "طفح", "جلدي بياكلني", "حبوب في جلدي", "itch", "itchy", "rash"],
    },
    "ring_lesion": {
        "name": "بقعة دائرية حوافها حمرا وأوضح من النص",
        "question": "هل في بقعة دائرية حوافها حمرا وبتكبر ببطء؟",
        "synonyms": ["بقعه دائريه", "دائره حمرا", "ringworm", "ring"],
    },
    "between_toes": {
        "name": "تقشير وهرش بين صوابع الرجل",
        "question": "هل في تقشير أو هرش أو بياض بين صوابع رجلك؟",
        "synonyms": ["بين صوابعي", "صوابع رجلي", "قدم الرياضي", "athlete's foot", "between toes"],
    },
    "red_eye": {
        "name": "احمرار العين",
        "question": "هل عينك حمرا؟",
        "synonyms": ["عيني حمرا", "احمرار العين", "عيني محمره", "red eye", "pink eye"],
    },
    "watery_eyes": {
        "name": "دموع كتير",
        "question": "هل عينك بتدمع كتير؟",
        "synonyms": ["عيني بتدمع", "دموع", "watery eyes", "tearing"],
    },
    "eye_discharge": {
        "name": "إفرازات صفرا أو خضرا من العين (عماص)",
        "question": "هل في إفرازات صفرا أو خضرا (عماص) بتلزق العين الصبح؟",
        "synonyms": ["عماص", "افرازات من عيني", "عيني لازقه", "eye discharge", "sticky eye"],
    },
}

# ---------------------------------------------------------------------------
# 2) الحالات المرضية + احتمالات الأعراض  P(symptom | condition)
# ---------------------------------------------------------------------------
# prior: الانتشار النسبي للحالة بين المرضى اللي بيدخلوا الصيدلية (تقدير)
# likelihoods: احتمال وجود العرض لو المريض عنده الحالة دي
# max_days: لو الأعراض مكملة أكتر من كده يبقى لازم دكتور
CONDITIONS = {
    "common_cold": {
        "name": "نزلة برد عادية (Common Cold)",
        "prior": 0.16,
        "max_days": 10,
        "likelihoods": {
            "runny_nose": 0.90, "nasal_congestion": 0.85, "sneezing": 0.75, "sore_throat": 0.60,
            "cough": 0.50, "cough_dry": 0.35, "headache": 0.35, "fever": 0.20, "high_fever": 0.03,
            "fatigue": 0.40, "body_aches": 0.20, "chills": 0.10, "watery_eyes": 0.30,
            "itchy_eyes_nose": 0.15, "seasonal_trigger": 0.10, "loss_smell": 0.20,
        },
        "advice": [
            "راحة وشرب سوائل دافية كتير (ينسون، ليمون بالعسل).",
            "غرغرة بمية دافية وملح لو الزور بيوجعك.",
            "بخار مية دافية بيساعد في فتح الأنف.",
            "نزلة البرد فيروسية وبتخف لوحدها خلال 7-10 أيام، والمضاد الحيوي مش بيفيد فيها.",
        ],
        "drugs": ["paracetamol", "saline_spray", "xylometazoline", "pseudoephedrine_combo", "lozenges", "zinc_vitc"],
        "refer_if": ["الأعراض كملت أكتر من 10 أيام", "حرارة عالية أكتر من 3 أيام", "ألم في الودن أو الجيوب الأنفية شديد"],
    },
    "influenza": {
        "name": "إنفلونزا (Influenza)",
        "prior": 0.09,
        "max_days": 7,
        "likelihoods": {
            "fever": 0.90, "high_fever": 0.70, "chills": 0.75, "body_aches": 0.85, "fatigue": 0.85,
            "headache": 0.70, "cough": 0.80, "cough_dry": 0.70, "sore_throat": 0.50,
            "runny_nose": 0.40, "nasal_congestion": 0.35, "sneezing": 0.15, "loss_smell": 0.15,
            "nausea": 0.10, "vomiting": 0.05,
        },
        "advice": [
            "راحة تامة في البيت وابعد عن الناس عشان العدوى.",
            "سوائل كتير جداً لتعويض الحرارة.",
            "كمادات مية فاترة (مش ساقعة) للحرارة.",
            "كبار السن والحوامل وأصحاب الأمراض المزمنة لازم يكلموا دكتور خلال 48 ساعة (ممكن يحتاجوا مضاد فيروسات بروشتة زي Oseltamivir).",
        ],
        "drugs": ["paracetamol", "ibuprofen", "saline_spray", "lozenges"],
        "refer_if": ["ضيق تنفس", "الحرارة مكملة أكتر من 3 أيام", "المريض فوق 65 سنة أو حامل أو عنده مرض مزمن"],
    },
    "allergic_rhinitis": {
        "name": "حساسية الأنف (Allergic Rhinitis)",
        "prior": 0.09,
        "max_days": 30,
        "likelihoods": {
            "sneezing": 0.90, "runny_nose": 0.85, "itchy_eyes_nose": 0.85, "nasal_congestion": 0.70,
            "watery_eyes": 0.65, "seasonal_trigger": 0.80, "red_eye": 0.25, "fever": 0.02,
            "high_fever": 0.01, "body_aches": 0.03, "sore_throat": 0.15, "cough": 0.15, "headache": 0.20,
            "fatigue": 0.25,
        },
        "advice": [
            "حاول تبعد عن المسبب (تراب، غبار، دخان، ريحة برفانات).",
            "اقفل الشبابيك في أيام التراب والخماسين.",
            "اغسل الأنف بمحلول ملح بانتظام.",
            "مضادات الهيستامين الحديثة (الجيل التاني) مش بتعمل نعاس زي القديمة.",
        ],
        "drugs": ["loratadine", "cetirizine", "saline_spray", "ketotifen_eye"],
        "refer_if": ["لو مصاحبها صفير في الصدر أو ضيق تنفس (احتمال ربو)", "مفيش تحسن بعد أسبوعين علاج"],
    },
    "pharyngitis": {
        "name": "التهاب الحلق (Pharyngitis / Sore Throat)",
        "prior": 0.08,
        "max_days": 7,
        "likelihoods": {
            "sore_throat": 0.97, "swollen_tonsils": 0.45, "fever": 0.45, "high_fever": 0.15,
            "headache": 0.30, "cough": 0.25, "runny_nose": 0.25, "fatigue": 0.35, "body_aches": 0.20,
            "chills": 0.20, "nasal_congestion": 0.20,
        },
        "advice": [
            "غرغرة بمية دافية وملح 3-4 مرات في اليوم.",
            "مشروبات دافية وعسل (للكبار والأطفال فوق سنة).",
            "معظم حالات التهاب الحلق فيروسية ومش محتاجة مضاد حيوي.",
            "لو في صديد على اللوز + حرارة + مفيش كحة (Centor criteria) يبقى لازم دكتور يقيّم الحاجة لمضاد حيوي.",
        ],
        "drugs": ["paracetamol", "ibuprofen", "lozenges", "benzydamine"],
        "refer_if": ["صعوبة شديدة في البلع أو فتح البق", "نقط بيضا/صديد على اللوز مع حرارة", "الأعراض أكتر من أسبوع"],
    },
    "acute_bronchitis": {
        "name": "كحة حادة / نزلة شعبية بسيطة (Acute Cough)",
        "prior": 0.07,
        "max_days": 21,
        "likelihoods": {
            "cough": 0.98, "cough_productive": 0.65, "cough_dry": 0.40, "chest_tightness": 0.45,
            "fever": 0.25, "high_fever": 0.05, "fatigue": 0.45, "sore_throat": 0.35, "runny_nose": 0.30,
            "body_aches": 0.20, "headache": 0.20, "nasal_congestion": 0.25,
        },
        "advice": [
            "سوائل دافية كتير بتخفف البلغم.",
            "ملعقة عسل قبل النوم بتهدي الكحة (ممنوع للأطفال أقل من سنة).",
            "ابعد عن التدخين والدخان تماماً.",
            "الكحة ممكن تفضل 2-3 أسابيع حتى بعد ما الالتهاب يخف وده طبيعي.",
        ],
        "drugs": ["ambroxol", "dextromethorphan", "paracetamol", "honey"],
        "refer_if": ["كحة بدم", "ضيق تنفس أو صفير", "الكحة أكتر من 3 أسابيع", "حرارة عالية مستمرة"],
    },
    "gastroenteritis": {
        "name": "نزلة معوية / إسهال حاد (Acute Gastroenteritis)",
        "prior": 0.09,
        "max_days": 3,
        "likelihoods": {
            "diarrhea": 0.95, "abdominal_cramps": 0.80, "nausea": 0.65, "vomiting": 0.50,
            "fever": 0.30, "high_fever": 0.05, "food_trigger": 0.55, "bloating": 0.40, "fatigue": 0.45,
            "body_aches": 0.15, "headache": 0.20, "epigastric_pain": 0.20, "chills": 0.10,
        },
        "advice": [
            "أهم حاجة تعويض السوائل: محلول معالجة الجفاف (ORS) بعد كل مرة إسهال.",
            "كُل أكل خفيف: رز، موز، توست، زبادي.",
            "ابعد عن الألبان الكاملة والمقليات والمشروبات الغازية والقهوة مؤقتاً.",
            "اغسل إيدك كويس عشان العدوى متتنقلش.",
        ],
        "drugs": ["ors", "nifuroxazide", "loperamide", "probiotic", "zinc_children", "paracetamol"],
        "refer_if": ["دم في البراز أو براز أسود", "علامات جفاف (مفيش بول، دوخة شديدة، بق ناشف جداً)", "الإسهال أكتر من 3 أيام", "طفل أقل من 6 شهور أو كبير سن"],
    },
    "constipation": {
        "name": "إمساك (Constipation)",
        "prior": 0.07,
        "max_days": 14,
        "likelihoods": {
            "constipation": 0.97, "hard_stool": 0.85, "bloating": 0.60, "abdominal_cramps": 0.40,
            "low_fiber": 0.70, "lower_abdominal_pain": 0.25, "fatigue": 0.15, "nausea": 0.10,
            "diarrhea": 0.02,
        },
        "advice": [
            "اشرب 8 كوبايات مية في اليوم على الأقل.",
            "زوّد الألياف: خضار، فاكهة، عيش بلدي/سن، بقوليات، شوفان.",
            "حركة ومشي نص ساعة يومياً.",
            "متأجلش دخول الحمام لما تحس بالرغبة.",
        ],
        "drugs": ["lactulose", "psyllium", "glycerin_supp", "bisacodyl"],
        "refer_if": ["دم في البراز", "نزول في الوزن من غير سبب", "تغيير مفاجئ في عادة الإخراج فوق سن 50", "مفيش تحسن بعد أسبوعين"],
    },
    "gerd": {
        "name": "حموضة وارتجاع (Heartburn / GERD / Dyspepsia)",
        "prior": 0.09,
        "max_days": 14,
        "likelihoods": {
            "heartburn": 0.95, "regurgitation": 0.70, "epigastric_pain": 0.60, "worse_lying": 0.70,
            "bloating": 0.40, "nausea": 0.25, "cough_dry": 0.10, "cough": 0.10, "sore_throat": 0.10,
            "vomiting": 0.05,
        },
        "advice": [
            "قسّم الأكل لوجبات صغيرة ومتنامش قبل 3 ساعات من الأكل.",
            "علّي راسك وانت نايم (مخدة زيادة أو رفع راس السرير).",
            "قلل القهوة والشاي والمشروبات الغازية والحار والدهون والشوكولاتة.",
            "التدخين والوزن الزيادة من أهم أسباب الارتجاع.",
        ],
        "drugs": ["alginate_antacid", "famotidine", "omeprazole"],
        "refer_if": ["صعوبة أو ألم في البلع", "ترجيع دم أو براز أسود", "نزول وزن", "سن فوق 55 مع أعراض جديدة", "مفيش تحسن بعد أسبوعين"],
    },
    "tension_headache": {
        "name": "صداع توتري (Tension-Type Headache)",
        "prior": 0.08,
        "max_days": 7,
        "likelihoods": {
            "headache": 0.99, "band_headache": 0.80, "stress": 0.75, "fatigue": 0.40,
            "one_sided_headache": 0.10, "photophobia": 0.10, "nausea": 0.05, "fever": 0.02,
        },
        "advice": [
            "راحة ونوم كافي (7-8 ساعات).",
            "قلل الشاشات وخد بريك كل ساعة لو بتذاكر أو بتشتغل على الكمبيوتر.",
            "اشرب مية كفاية - الجفاف من أشهر أسباب الصداع.",
            "متاخدش مسكنات أكتر من 2-3 أيام في الأسبوع عشان ميحصلش صداع من كتر المسكنات (Medication Overuse Headache).",
        ],
        "drugs": ["paracetamol", "ibuprofen", "paracetamol_caffeine"],
        "refer_if": ["صداع مفاجئ شديد جداً", "صداع مع حرارة وتيبس رقبة", "صداع بيصحيك من النوم أو بيزيد كل يوم"],
    },
    "migraine": {
        "name": "صداع نصفي (Migraine)",
        "prior": 0.05,
        "max_days": 3,
        "likelihoods": {
            "headache": 0.99, "one_sided_headache": 0.80, "photophobia": 0.85, "nausea": 0.70,
            "vomiting": 0.30, "band_headache": 0.10, "stress": 0.40, "fatigue": 0.35, "fever": 0.02,
        },
        "advice": [
            "نام في أوضة ضلمة وهادية أول ما النوبة تبدأ.",
            "خد المسكن بدري في أول النوبة - بيكون مفعوله أحسن بكتير.",
            "اعمل مذكرة صداع (Headache diary) تعرف منها المحفزات: قلة نوم، جوع، شوكولاتة، قهوة...",
            "لو النوبات أكتر من 4 في الشهر لازم دكتور مخ وأعصاب لعلاج وقائي.",
        ],
        "drugs": ["ibuprofen", "paracetamol", "paracetamol_caffeine", "domperidone"],
        "refer_if": ["أول مرة يحصل فوق سن 50", "صداع مع ضعف أو تنميل في نص الجسم", "تغيير في شكل الصداع المعتاد"],
    },
    "uti": {
        "name": "التهاب المثانة البسيط (Lower UTI / Cystitis)",
        "prior": 0.05,
        "max_days": 2,
        "likelihoods": {
            "dysuria": 0.95, "urinary_frequency": 0.85, "lower_abdominal_pain": 0.60, "fever": 0.15,
            "high_fever": 0.03, "fatigue": 0.20, "abdominal_cramps": 0.15, "nausea": 0.05,
        },
        "advice": [
            "اشرب مية كتير جداً (2-3 لتر في اليوم).",
            "متحبسش البول.",
            "التهاب المثانة غالباً محتاج مضاد حيوي بروشتة - لازم دكتور.",
            "منتجات التوت البري (Cranberry) ممكن تساعد في الوقاية بس مش علاج.",
        ],
        "drugs": ["paracetamol", "urinary_alkalinizer"],
        "refer_if": ["دايماً محتاج دكتور للمضاد الحيوي", "راجل أو حامل أو طفل (لازم تحويل فوري)", "حرارة أو ألم في الضهر/الجنب (احتمال التهاب كلى)", "دم في البول"],
        "always_refer": True,
    },
    "dysmenorrhea": {
        "name": "ألم الدورة الشهرية (Primary Dysmenorrhea)",
        "prior": 0.05,
        "max_days": 3,
        "likelihoods": {
            "menstrual_pain": 0.98, "lower_abdominal_pain": 0.90, "abdominal_cramps": 0.85,
            "headache": 0.30, "nausea": 0.30, "fatigue": 0.40, "bloating": 0.45, "diarrhea": 0.15,
            "vomiting": 0.08,
        },
        "advice": [
            "قربة مية دافية على أسفل البطن.",
            "مشروبات دافية زي القرفة والنعناع.",
            "الرياضة الخفيفة بانتظام بتقلل الألم على المدى الطويل.",
            "مضادات الالتهاب (NSAIDs) هي الخط الأول لأنها بتقلل البروستاجلاندين المسؤول عن الألم - ابدأيها قبل الألم بيوم أو أول ما يبدأ.",
        ],
        "drugs": ["mefenamic_acid", "ibuprofen", "hyoscine", "paracetamol"],
        "refer_if": ["ألم شديد مش بيستجيب للمسكنات", "نزيف غزير جداً", "ألم في غير ميعاد الدورة", "احتمال حمل"],
    },
    "tinea": {
        "name": "فطريات جلدية (Tinea / Fungal Skin Infection)",
        "prior": 0.04,
        "max_days": 28,
        "likelihoods": {
            "itchy_rash": 0.90, "ring_lesion": 0.70, "between_toes": 0.50, "fever": 0.01,
            "red_eye": 0.01,
        },
        "advice": [
            "حافظ على المكان ناشف ونضيف - نشّف كويس بعد الاستحمام خصوصاً بين الصوابع.",
            "البس شرابات قطن وغيّرها يومياً.",
            "متستخدمش فوطة حد تاني.",
            "كمّل الكريم أسبوعين بعد ما الجلد يرجع طبيعي عشان الفطريات متجيش تاني.",
        ],
        "drugs": ["clotrimazole", "miconazole", "terbinafine_cream"],
        "refer_if": ["الفطريات في فروة الراس أو الضوافر (محتاجة علاج بالبق)", "مريض سكر عنده جرح في رجله", "مفيش تحسن بعد أسبوعين"],
    },
    "allergic_conjunctivitis": {
        "name": "حساسية العين (Allergic Conjunctivitis)",
        "prior": 0.03,
        "max_days": 14,
        "likelihoods": {
            "red_eye": 0.90, "itchy_eyes_nose": 0.95, "watery_eyes": 0.85, "seasonal_trigger": 0.75,
            "sneezing": 0.45, "runny_nose": 0.40, "eye_discharge": 0.10, "fever": 0.01,
        },
        "advice": [
            "كمادات مية ساقعة على العين.",
            "متدعكش عينك.",
            "شيل العدسات اللاصقة لحد ما تخف.",
            "دموع صناعية بتغسل مسببات الحساسية من العين.",
        ],
        "drugs": ["ketotifen_eye", "artificial_tears", "loratadine"],
        "refer_if": ["ألم في العين أو زغللة في النظر", "حساسية من النور", "عين واحدة بس حمرا جداً"],
    },
    "bacterial_conjunctivitis": {
        "name": "التهاب ملتحمة بكتيري (Bacterial Conjunctivitis)",
        "prior": 0.02,
        "max_days": 5,
        "likelihoods": {
            "red_eye": 0.95, "eye_discharge": 0.90, "watery_eyes": 0.40, "itchy_eyes_nose": 0.25,
            "seasonal_trigger": 0.05, "fever": 0.05,
        },
        "advice": [
            "نضّف العين بقطنة ومية مغلية ومتبردة (قطنة لكل عين).",
            "متشاركش الفوط والمخدات - معدي جداً.",
            "شيل العدسات اللاصقة.",
            "غالباً محتاج قطرة مضاد حيوي بروشتة من الدكتور.",
        ],
        "drugs": ["artificial_tears"],
        "refer_if": ["دايماً للدكتور لتقييم قطرة المضاد الحيوي", "ألم أو زغللة", "طفل حديث الولادة"],
        "always_refer": True,
    },
}

# فئة "حالة غير مدرجة" - بتمثل أي مرض تاني خارج قاعدة المعرفة.
# لو كسبت يبقى النظام مش متأكد ولازم يحوّل للدكتور (Open-world safety).
UNKNOWN_CONDITION = {
    "name": "حالة غير واضحة / خارج نطاق النظام",
    "prior": 0.04,
    "default_likelihood": 0.12,
}

# احتمال وجود عرض مش مذكور لحالة معينة (Leak probability)
LEAK_PROBABILITY = 0.005

# ---------------------------------------------------------------------------
# 3) الأدوية بدون روشتة (OTC)
# ---------------------------------------------------------------------------
# avoid_if  : أمراض/حالات تمنع الدواء تماماً
# caution_if: أمراض/حالات محتاجة حذر أو استشارة
# min_age   : أقل سن بالسنين
# group     : المجموعة الدوائية (بتستخدم في التداخلات)
DRUGS = {
    "paracetamol": {
        "generic": "Paracetamol (Acetaminophen)",
        "brands": "Panadol, Abimol, Paramol, Cetal",
        "group": "paracetamol",
        "use": "مسكن وخافض حرارة",
        "adult_dose": "500 - 1000 مجم كل 4-6 ساعات، بحد أقصى 4 جرام في اليوم (8 أقراص 500)",
        "child_dose": "15 مجم/كجم كل 4-6 ساعات، بحد أقصى 4 جرعات في اليوم",
        "min_age": 0.25,
        "avoid_if": [],
        "caution_if": ["liver"],
        "notes": "آمن في الحمل والرضاعة بالجرعات العادية. اقرأ مكونات أدوية البرد عشان متاخدش باراسيتامول مرتين.",
    },
    "paracetamol_caffeine": {
        "generic": "Paracetamol + Caffeine",
        "brands": "Panadol Extra, Solpadeine",
        "group": "paracetamol",
        "use": "مسكن أقوى للصداع",
        "adult_dose": "قرص أو قرصين كل 4-6 ساعات، بحد أقصى 8 أقراص في اليوم",
        "child_dose": "غير مناسب لأقل من 12 سنة",
        "min_age": 12,
        "avoid_if": [],
        "caution_if": ["liver", "heart_disease", "pregnancy", "hypertension"],
        "notes": "متاخدوش بالليل عشان الكافيين ممكن يسبب أرق.",
    },
    "ibuprofen": {
        "generic": "Ibuprofen",
        "brands": "Brufen, Ibuprofen, Marcofen",
        "group": "nsaid",
        "use": "مسكن ومضاد للالتهاب وخافض حرارة",
        "adult_dose": "200 - 400 مجم كل 6-8 ساعات بعد الأكل، بحد أقصى 1200 مجم في اليوم بدون روشتة",
        "child_dose": "10 مجم/كجم كل 6-8 ساعات بعد الأكل (من سن 6 شهور)",
        "min_age": 0.5,
        "avoid_if": ["peptic_ulcer", "kidney", "pregnancy", "nsaid_allergy", "heart_disease"],
        "caution_if": ["asthma", "hypertension", "breastfeeding", "liver"],
        "notes": "لازم بعد الأكل. ممنوع في الجفاف الشديد (إسهال/ترجيع كتير) لأنه بيأثر على الكلى.",
    },
    "mefenamic_acid": {
        "generic": "Mefenamic Acid",
        "brands": "Ponstan, Ponstan Forte",
        "group": "nsaid",
        "use": "مضاد التهاب ممتاز لألم الدورة",
        "adult_dose": "500 مجم 3 مرات في اليوم بعد الأكل، لمدة أقصاها 3 أيام",
        "child_dose": "غير مناسب لأقل من 12 سنة بدون دكتور",
        "min_age": 12,
        "avoid_if": ["peptic_ulcer", "kidney", "pregnancy", "nsaid_allergy", "heart_disease"],
        "caution_if": ["asthma", "hypertension", "breastfeeding"],
        "notes": "ابدأي فيه أول ما الألم يبدأ أو قبله بيوم.",
    },
    "hyoscine": {
        "generic": "Hyoscine Butylbromide",
        "brands": "Buscopan",
        "group": "antispasmodic",
        "use": "مضاد للتقلصات والمغص",
        "adult_dose": "10 - 20 مجم 3-4 مرات في اليوم، بحد أقصى 80 مجم",
        "child_dose": "من 6-12 سنة: 10 مجم 3 مرات في اليوم",
        "min_age": 6,
        "avoid_if": ["glaucoma", "bph"],
        "caution_if": ["heart_disease", "pregnancy"],
        "notes": "ممكن يسبب نشفان في البق وإمساك خفيف.",
    },
    "saline_spray": {
        "generic": "Sodium Chloride 0.9% Nasal Spray",
        "brands": "Sterimar, Otrivin Saline, Physiomer",
        "group": "saline",
        "use": "غسيل وترطيب الأنف",
        "adult_dose": "بخة أو اتنين في كل فتحة عدة مرات في اليوم",
        "child_dose": "آمن لكل الأعمار (نقط للرضع)",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": [],
        "notes": "آمن تماماً حتى للحوامل والرضع.",
    },
    "xylometazoline": {
        "generic": "Xylometazoline 0.1% Nasal Spray",
        "brands": "Otrivin",
        "group": "decongestant_topical",
        "use": "مزيل احتقان سريع للأنف",
        "adult_dose": "بخة في كل فتحة 2-3 مرات في اليوم، لمدة أقصاها 5 أيام",
        "child_dose": "تركيز 0.05% للأطفال من 6-12 سنة",
        "min_age": 6,
        "avoid_if": ["glaucoma"],
        "caution_if": ["hypertension", "heart_disease", "pregnancy"],
        "notes": "استخدامه أكتر من 5 أيام بيعمل احتقان ارتدادي (Rhinitis Medicamentosa).",
    },
    "pseudoephedrine_combo": {
        "generic": "Paracetamol + Pseudoephedrine + Chlorpheniramine",
        "brands": "Congestal, Comtrex, 1-2-3",
        "group": "decongestant_oral",
        "also": ["paracetamol"],
        "use": "مركب للبرد (مسكن + مزيل احتقان + مضاد حساسية)",
        "adult_dose": "قرص كل 6-8 ساعات، بحد أقصى 4 أقراص في اليوم",
        "child_dose": "غير مناسب لأقل من 12 سنة",
        "min_age": 12,
        "avoid_if": ["hypertension", "heart_disease", "glaucoma", "bph", "pregnancy"],
        "caution_if": ["diabetes", "breastfeeding", "liver"],
        "notes": "بيسبب نعاس - متسوقش بعده. فيه باراسيتامول فمتاخدش معاه بانادول.",
    },
    "lozenges": {
        "generic": "Amylmetacresol + Dichlorobenzyl alcohol Lozenges",
        "brands": "Strepsils",
        "group": "lozenge",
        "use": "أقراص استحلاب مطهرة للزور",
        "adult_dose": "قرص كل 2-3 ساعات، بحد أقصى 8 أقراص في اليوم",
        "child_dose": "من سن 6 سنين",
        "min_age": 6,
        "avoid_if": [],
        "caution_if": ["diabetes"],
        "notes": "لمرضى السكر في أنواع خالية من السكر (Sugar-free).",
    },
    "benzydamine": {
        "generic": "Benzydamine Mouthwash/Spray",
        "brands": "Tantum Verde",
        "group": "local_antiinflammatory",
        "use": "غرغرة/بخاخ مضاد التهاب ومخدر موضعي للزور",
        "adult_dose": "غرغرة 15 مل كل 2-3 ساعات (متتبلعش)",
        "child_dose": "البخاخ من سن 6 سنين",
        "min_age": 6,
        "avoid_if": [],
        "caution_if": [],
        "notes": "ممكن يعمل تنميل خفيف في البق وده طبيعي.",
    },
    "zinc_vitc": {
        "generic": "Vitamin C + Zinc",
        "brands": "C-Retard, Cevarol, Zinc tablets",
        "group": "supplement",
        "use": "مكمل غذائي ممكن يقصّر مدة البرد شوية",
        "adult_dose": "فيتامين سي 500-1000 مجم + زنك 10-25 مجم يومياً لمدة أسبوع",
        "child_dose": "حسب الجرعة المناسبة للسن",
        "min_age": 2,
        "avoid_if": [],
        "caution_if": ["kidney"],
        "notes": "مكمل مساعد مش علاج أساسي.",
    },
    "loratadine": {
        "generic": "Loratadine",
        "brands": "Claritine, Lorano",
        "group": "antihistamine",
        "use": "مضاد هيستامين (جيل تاني - مش بيعمل نعاس)",
        "adult_dose": "10 مجم مرة واحدة في اليوم",
        "child_dose": "2-12 سنة: 5 مجم (لو الوزن أقل من 30 كجم) أو 10 مجم (لو أكتر)",
        "min_age": 2,
        "avoid_if": [],
        "caution_if": ["liver", "pregnancy"],
        "notes": "من أأمن مضادات الهيستامين في الحمل لكن بعد استشارة الدكتور.",
    },
    "cetirizine": {
        "generic": "Cetirizine",
        "brands": "Zyrtec, Histazine",
        "group": "antihistamine",
        "use": "مضاد هيستامين (جيل تاني)",
        "adult_dose": "10 مجم مرة واحدة في اليوم (يفضل بالليل)",
        "child_dose": "2-6 سنين: 2.5 مجم مرتين، 6-12 سنة: 5 مجم مرتين",
        "min_age": 2,
        "avoid_if": [],
        "caution_if": ["kidney", "pregnancy"],
        "notes": "ممكن يعمل نعاس خفيف عند بعض الناس.",
    },
    "ketotifen_eye": {
        "generic": "Ketotifen 0.025% Eye Drops",
        "brands": "Zaditen eye drops",
        "group": "eye_antihistamine",
        "use": "قطرة مضاد حساسية للعين",
        "adult_dose": "نقطة في كل عين مرتين في اليوم",
        "child_dose": "من سن 3 سنين",
        "min_age": 3,
        "avoid_if": [],
        "caution_if": [],
        "notes": "شيل العدسات اللاصقة واستنى ربع ساعة قبل ما ترجعها.",
    },
    "artificial_tears": {
        "generic": "Artificial Tears (Hypromellose / Carboxymethylcellulose)",
        "brands": "Tears Guard, Refresh Tears, Systane",
        "group": "lubricant",
        "use": "دموع صناعية مرطبة",
        "adult_dose": "نقطة أو اتنين في العين حسب الحاجة",
        "child_dose": "آمنة",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": [],
        "notes": "آمنة جداً.",
    },
    "ambroxol": {
        "generic": "Ambroxol",
        "brands": "Mucosolvan",
        "group": "mucolytic",
        "use": "مذيب للبلغم",
        "adult_dose": "30 مجم 3 مرات في اليوم",
        "child_dose": "2-5 سنين: 7.5 مجم 3 مرات، 6-12 سنة: 15 مجم 2-3 مرات",
        "min_age": 2,
        "avoid_if": [],
        "caution_if": ["peptic_ulcer", "pregnancy"],
        "notes": "للكحة اللي فيها بلغم بس - ميتاخدش مع مهدئ كحة.",
    },
    "dextromethorphan": {
        "generic": "Dextromethorphan",
        "brands": "Tusskan, Dextromethorphan syrups",
        "group": "antitussive",
        "use": "مهدئ للكحة الناشفة",
        "adult_dose": "15 - 30 مجم كل 6-8 ساعات، بحد أقصى 120 مجم في اليوم",
        "child_dose": "غير مناسب لأقل من 6 سنين",
        "min_age": 6,
        "avoid_if": [],
        "caution_if": ["asthma", "pregnancy", "liver"],
        "notes": "للكحة الناشفة بس. ممنوع مع البلغم لأنه بيحبس البلغم في الصدر.",
    },
    "honey": {
        "generic": "Honey (Natural remedy)",
        "brands": "عسل نحل طبيعي",
        "group": "natural",
        "use": "مهدئ طبيعي للكحة والزور",
        "adult_dose": "ملعقة كبيرة قبل النوم أو في مشروب دافي",
        "child_dose": "نص ملعقة صغيرة للأطفال فوق سنة",
        "min_age": 1,
        "avoid_if": [],
        "caution_if": ["diabetes"],
        "notes": "ممنوع تماماً للأطفال أقل من سنة (خطر التسمم البوتشيليني).",
    },
    "ors": {
        "generic": "Oral Rehydration Salts (ORS)",
        "brands": "Rehydran",
        "group": "ors",
        "use": "تعويض السوائل والأملاح - أهم علاج للإسهال",
        "adult_dose": "كيس في 200 مل مية بعد كل مرة إسهال",
        "child_dose": "50-100 مل/كجم على 4 ساعات للجفاف البسيط، أو 10 مل/كجم بعد كل مرة إسهال",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": ["kidney", "heart_disease"],
        "notes": "حضّره بالمية المغلية المتبردة بالمقدار المظبوط بالظبط.",
    },
    "nifuroxazide": {
        "generic": "Nifuroxazide",
        "brands": "Antinal",
        "group": "intestinal_antiseptic",
        "use": "مطهر معوي للإسهال البكتيري",
        "adult_dose": "200 مجم كل 6 ساعات لمدة أقصاها 7 أيام",
        "child_dose": "حسب نشرة الشراب حسب السن",
        "min_age": 2,
        "avoid_if": [],
        "caution_if": ["pregnancy"],
        "notes": "بيشتغل جوه الأمعاء ومش بيتمتص في الدم. مش بديل عن محلول الجفاف.",
    },
    "loperamide": {
        "generic": "Loperamide",
        "brands": "Imodium",
        "group": "antidiarrheal",
        "use": "مضاد إسهال سريع",
        "adult_dose": "4 مجم أول جرعة ثم 2 مجم بعد كل مرة إسهال، بحد أقصى 8 مجم في اليوم بدون روشتة",
        "child_dose": "غير مناسب لأقل من 12 سنة",
        "min_age": 12,
        "avoid_if": ["fever_present", "liver"],
        "caution_if": ["pregnancy"],
        "notes": "ممنوع لو في حرارة أو دم في البراز (ممكن يحبس الميكروب جوه).",
    },
    "probiotic": {
        "generic": "Probiotic (Lactobacillus / Bacillus clausii)",
        "brands": "Lacteol Forte, Enterogermina",
        "group": "probiotic",
        "use": "بكتيريا نافعة لتقصير مدة الإسهال",
        "adult_dose": "كيس أو كبسولة مرتين في اليوم",
        "child_dose": "آمن للأطفال",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": [],
        "notes": "آمن جداً.",
    },
    "zinc_children": {
        "generic": "Zinc Sulfate (للأطفال)",
        "brands": "Zinc syrup, Zinctron",
        "group": "supplement",
        "use": "توصية منظمة الصحة العالمية للأطفال مع الإسهال",
        "adult_dose": "غير مطلوب للكبار",
        "child_dose": "أقل من 6 شهور: 10 مجم/يوم، أكبر من 6 شهور: 20 مجم/يوم لمدة 10-14 يوم",
        "min_age": 0,
        "max_age": 12,
        "avoid_if": [],
        "caution_if": [],
        "notes": "بيقلل مدة وشدة الإسهال وبيمنع تكراره.",
    },
    "lactulose": {
        "generic": "Lactulose",
        "brands": "Duphalac, Lactulose",
        "group": "laxative_osmotic",
        "use": "ملين لطيف (بيسحب مية للأمعاء)",
        "adult_dose": "15 - 30 مل مرة أو مرتين في اليوم",
        "child_dose": "1-5 سنين: 5-10 مل، 5-10 سنين: 10-15 مل",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": ["diabetes"],
        "notes": "آمن في الحمل. مفعوله بيبدأ بعد 1-2 يوم. ممكن يعمل غازات في الأول.",
    },
    "psyllium": {
        "generic": "Psyllium Husk (Ispaghula)",
        "brands": "Fybogel, Psyllium",
        "group": "laxative_bulk",
        "use": "ألياف طبيعية بتكبّر حجم البراز",
        "adult_dose": "كيس في كوباية مية كبيرة مرة أو مرتين في اليوم",
        "child_dose": "من 6 سنين بنص الجرعة",
        "min_age": 6,
        "avoid_if": [],
        "caution_if": [],
        "notes": "لازم يتاخد مع مية كتير. آمن في الحمل.",
    },
    "glycerin_supp": {
        "generic": "Glycerin Suppositories",
        "brands": "Glycerin suppositories (أطفال/كبار)",
        "group": "laxative_rectal",
        "use": "لبوس ملين سريع المفعول",
        "adult_dose": "لبوس واحد عند اللزوم",
        "child_dose": "لبوس أطفال عند اللزوم",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": [],
        "notes": "مفعوله خلال 15-30 دقيقة.",
    },
    "bisacodyl": {
        "generic": "Bisacodyl",
        "brands": "Dulcolax, Bisadyl",
        "group": "laxative_stimulant",
        "use": "ملين منشط (للاستخدام قصير المدى)",
        "adult_dose": "5 - 10 مجم بالليل",
        "child_dose": "غير مناسب لأقل من 10 سنين بدون دكتور",
        "min_age": 10,
        "avoid_if": [],
        "caution_if": ["pregnancy"],
        "notes": "متاخدوش مع لبن أو مضاد حموضة (بيبوظ الغلاف). ميتاخدش أكتر من 5 أيام.",
    },
    "alginate_antacid": {
        "generic": "Sodium Alginate + Antacid",
        "brands": "Gaviscon",
        "group": "antacid",
        "use": "بيعمل طبقة فوق المعدة تمنع الارتجاع ويعادل الحموضة",
        "adult_dose": "10 - 20 مل بعد الأكل وقبل النوم",
        "child_dose": "من 6 سنين بنص الجرعة",
        "min_age": 6,
        "avoid_if": [],
        "caution_if": ["kidney", "hypertension"],
        "notes": "آمن في الحمل. سيب ساعتين بينه وبين أي دواء تاني.",
    },
    "famotidine": {
        "generic": "Famotidine",
        "brands": "Antodine",
        "group": "h2_blocker",
        "use": "بيقلل إفراز الحمض",
        "adult_dose": "20 مجم مرتين في اليوم لمدة أقصاها أسبوعين بدون دكتور",
        "child_dose": "غير مناسب لأقل من 16 سنة بدون دكتور",
        "min_age": 16,
        "avoid_if": [],
        "caution_if": ["kidney", "pregnancy"],
        "notes": "مرضى الكلى محتاجين جرعة أقل.",
    },
    "omeprazole": {
        "generic": "Omeprazole 20 mg",
        "brands": "Omez, Gastrazole",
        "group": "ppi",
        "use": "أقوى مقلل للحمض (مثبط مضخة البروتون)",
        "adult_dose": "20 مجم مرة في اليوم على الريق قبل الفطار بنص ساعة، لمدة 14 يوم",
        "child_dose": "غير مناسب لأقل من 18 سنة بدون دكتور",
        "min_age": 18,
        "avoid_if": [],
        "caution_if": ["liver", "pregnancy"],
        "notes": "مش للاستخدام الطويل من غير متابعة.",
    },
    "domperidone": {
        "generic": "Domperidone",
        "brands": "Motilium",
        "group": "antiemetic",
        "use": "مضاد للغثيان والترجيع",
        "adult_dose": "10 مجم حتى 3 مرات في اليوم قبل الأكل، لمدة أقصاها أسبوع",
        "child_dose": "غير مناسب لأقل من 12 سنة بدون دكتور",
        "min_age": 12,
        "avoid_if": ["heart_disease", "liver"],
        "caution_if": ["pregnancy", "breastfeeding"],
        "notes": "ممنوع مع أمراض القلب واضطرابات النبض.",
    },
    "urinary_alkalinizer": {
        "generic": "Potassium Citrate (Urinary Alkalinizer)",
        "brands": "Urosolvine, Uricol",
        "group": "alkalinizer",
        "use": "بيقلل حموضة البول ويخفف الحرقان مؤقتاً لحد زيارة الدكتور",
        "adult_dose": "حسب النشرة (كيس أو معلقتين في مية 3 مرات يومياً)",
        "child_dose": "بعد استشارة الدكتور",
        "min_age": 12,
        "avoid_if": ["kidney", "heart_disease"],
        "caution_if": ["hypertension"],
        "notes": "ده بيخفف الأعراض بس - مش علاج للالتهاب.",
    },
    "clotrimazole": {
        "generic": "Clotrimazole 1% Cream",
        "brands": "Canesten",
        "group": "antifungal_topical",
        "use": "كريم مضاد للفطريات",
        "adult_dose": "دهان طبقة رفيعة 2-3 مرات في اليوم لمدة 2-4 أسابيع",
        "child_dose": "آمن للأطفال",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": [],
        "notes": "كمّل أسبوعين بعد ما الجلد يرجع طبيعي.",
    },
    "miconazole": {
        "generic": "Miconazole 2% Cream",
        "brands": "Daktarin",
        "group": "antifungal_topical",
        "use": "كريم مضاد للفطريات",
        "adult_dose": "دهان مرتين في اليوم لمدة 2-6 أسابيع",
        "child_dose": "آمن للأطفال",
        "min_age": 0,
        "avoid_if": [],
        "caution_if": [],
        "notes": "الكريم الجلدي امتصاصه ضعيف، أما جل البق بيتداخل مع الوارفارين.",
    },
    "terbinafine_cream": {
        "generic": "Terbinafine 1% Cream",
        "brands": "Lamisil",
        "group": "antifungal_topical",
        "use": "كريم مضاد للفطريات (مدة علاج أقصر)",
        "adult_dose": "دهان مرة أو مرتين في اليوم لمدة 1-2 أسبوع",
        "child_dose": "من سن 12 سنة",
        "min_age": 12,
        "avoid_if": [],
        "caution_if": ["pregnancy"],
        "notes": "ممتاز لقدم الرياضي.",
    },
}

# ---------------------------------------------------------------------------
# 4) الحالات المرضية للمريض (Patient Profile)
# ---------------------------------------------------------------------------
PATIENT_CONDITIONS = {
    "pregnancy": "حمل",
    "breastfeeding": "رضاعة طبيعية",
    "peptic_ulcer": "قرحة معدة أو نزيف معدة سابق",
    "kidney": "مرض في الكلى",
    "liver": "مرض في الكبد",
    "asthma": "ربو / حساسية صدر",
    "hypertension": "ضغط عالي",
    "heart_disease": "مرض في القلب",
    "diabetes": "سكر",
    "glaucoma": "مياه زرقا على العين (جلوكوما)",
    "bph": "تضخم البروستاتا",
    "nsaid_allergy": "حساسية من الأسبرين أو المسكنات (NSAIDs)",
}

# ---------------------------------------------------------------------------
# 5) الأدوية المزمنة (لفحص التداخلات)
# ---------------------------------------------------------------------------
CHRONIC_MEDS = {
    "warfarin": {"name": "Warfarin (Marevan) - سيولة", "group": "anticoagulant"},
    "aspirin_low": {"name": "Aspirin 75mg (Aspocid) - سيولة", "group": "antiplatelet"},
    "clopidogrel": {"name": "Clopidogrel (Plavix) - سيولة", "group": "clopidogrel"},
    "ssri": {"name": "Fluoxetine/Sertraline/Escitalopram - اكتئاب (SSRI)", "group": "ssri"},
    "maoi": {"name": "MAO Inhibitors - اكتئاب (MAOI)", "group": "maoi"},
    "lithium": {"name": "Lithium - اضطراب ثنائي القطب", "group": "lithium"},
    "ace_inhibitor": {"name": "Captopril/Enalapril/Lisinopril - ضغط (ACEi/ARB)", "group": "ace_inhibitor"},
    "diuretic": {"name": "Furosemide/Hydrochlorothiazide - مدرات بول", "group": "diuretic"},
    "methotrexate": {"name": "Methotrexate - روماتيزم", "group": "methotrexate"},
    "levothyroxine": {"name": "Levothyroxine (Eltroxin) - غدة درقية", "group": "levothyroxine"},
    "ciprofloxacin": {"name": "Ciprofloxacin (Ciprobay) - مضاد حيوي", "group": "quinolone"},
    "digoxin": {"name": "Digoxin (Lanoxin) - قلب", "group": "digoxin"},
    "metformin": {"name": "Metformin (Cidophage/Glucophage) - سكر", "group": "metformin"},
    "iron": {"name": "Iron supplements (Ferrotron/Haemojet) - حديد", "group": "iron"},
}

# ---------------------------------------------------------------------------
# 6) التداخلات الدوائية (بين المجموعات)
# ---------------------------------------------------------------------------
# severity: major (خطير - ممنوع) / moderate (متوسط - محتاج حذر) / minor (بسيط)
INTERACTIONS = [
    ("nsaid", "anticoagulant", "major", "زيادة كبيرة في خطر النزيف (معدة ومخ).", "استخدم باراسيتامول بدلاً منه."),
    ("nsaid", "antiplatelet", "moderate", "زيادة خطر نزيف المعدة، والإيبوبروفين ممكن يقلل مفعول الأسبرين الوقائي للقلب.", "لو لازم: خد الأسبرين قبل الإيبوبروفين بساعتين، والأفضل باراسيتامول."),
    ("nsaid", "clopidogrel", "major", "زيادة خطر النزيف.", "استخدم باراسيتامول."),
    ("nsaid", "ssri", "moderate", "زيادة خطر نزيف المعدة.", "باراسيتامول أأمن، أو يتاخد مع واقي معدة بعد استشارة."),
    ("nsaid", "lithium", "major", "بيرفع مستوى الليثيوم في الدم لدرجة السمية.", "ممنوع - استخدم باراسيتامول."),
    ("nsaid", "ace_inhibitor", "moderate", "بيقلل مفعول دوا الضغط وممكن يأذي الكلى (خصوصاً مع مدرات البول = Triple Whammy).", "أقل جرعة لأقصر مدة، والأفضل باراسيتامول."),
    ("nsaid", "diuretic", "moderate", "بيقلل مفعول مدر البول وبيزود خطر أذى الكلى.", "الأفضل باراسيتامول."),
    ("nsaid", "methotrexate", "major", "بيقلل خروج الميثوتركسات ويزود سميته.", "ممنوع بدون دكتور."),
    ("paracetamol", "anticoagulant", "moderate", "الاستخدام المنتظم بجرعات عالية (أكتر من 2 جرام يومياً لكذا يوم) ممكن يرفع الـ INR.", "الجرعات العادية لفترة قصيرة مقبولة، مع متابعة الـ INR."),
    ("antitussive", "maoi", "major", "خطر متلازمة السيروتونين (حرارة، تشنجات، ممكن تكون قاتلة).", "ممنوع تماماً - ولمدة أسبوعين بعد وقف الـ MAOI."),
    ("antitussive", "ssri", "moderate", "خطر متلازمة السيروتونين.", "استخدم عسل أو مستحلبات بدلاً منه."),
    ("decongestant_oral", "maoi", "major", "خطر أزمة ارتفاع ضغط حادة.", "ممنوع تماماً."),
    ("decongestant_oral", "ace_inhibitor", "moderate", "بيرفع الضغط وبيقلل مفعول دوا الضغط.", "استخدم بخاخ ملح بدلاً منه."),
    ("decongestant_oral", "digoxin", "moderate", "خطر اضطراب نبض القلب.", "تجنبه."),
    ("decongestant_topical", "maoi", "moderate", "ممكن يرفع الضغط.", "تجنبه أو استخدم محلول ملح."),
    ("antacid", "levothyroxine", "moderate", "بيقلل امتصاص دوا الغدة.", "سيب 4 ساعات بينهم."),
    ("antacid", "quinolone", "major", "بيقلل امتصاص المضاد الحيوي لدرجة إنه ممكن ميشتغلش.", "خد السيبرو قبل مضاد الحموضة بساعتين أو بعده بـ 6 ساعات."),
    ("antacid", "iron", "moderate", "بيقلل امتصاص الحديد.", "سيب ساعتين بينهم."),
    ("antacid", "digoxin", "minor", "ممكن يقلل امتصاص الديجوكسين.", "سيب ساعتين بينهم."),
    ("ppi", "clopidogrel", "moderate", "الأوميبرازول بيقلل تفعيل الكلوبيدوجريل فيقل مفعوله في منع الجلطات.", "استخدم Pantoprazole أو Famotidine بدلاً منه بعد استشارة."),
    ("ppi", "methotrexate", "moderate", "ممكن يرفع مستوى الميثوتركسات.", "استشر الدكتور."),
    ("ppi", "iron", "minor", "بيقلل امتصاص الحديد على المدى الطويل.", "تابع مستوى الحديد."),
    ("h2_blocker", "iron", "minor", "ممكن يقلل امتصاص الحديد.", "سيب ساعتين بينهم."),
    ("laxative_stimulant", "antacid", "minor", "مضاد الحموضة بيدوب غلاف البيساكوديل فيهيّج المعدة.", "سيب ساعة على الأقل بينهم."),
    ("laxative_stimulant", "diuretic", "moderate", "خطر نقص البوتاسيوم.", "استخدم لاكتيولوز بدلاً منه."),
    ("antiemetic", "quinolone", "moderate", "زيادة خطر اضطراب نبض القلب (QT prolongation).", "تجنبه بدون دكتور."),
    ("antispasmodic", "antihistamine", "minor", "زيادة الأعراض المضادة للكولين (نشفان بق، إمساك، زغللة).", "انتبه للأعراض."),
    ("alkalinizer", "ace_inhibitor", "moderate", "خطر زيادة البوتاسيوم في الدم.", "متاخدش سترات البوتاسيوم بدون دكتور."),
    ("alkalinizer", "quinolone", "minor", "قلوية البول ممكن تقلل ذوبان السيبرو في البول.", "استشر الدكتور."),
    ("nsaid", "nsaid", "major", "أخد اتنين مسكن من نفس العيلة بيضاعف الأضرار من غير فايدة زيادة.", "استخدم نوع واحد بس."),
    ("paracetamol", "paracetamol", "major", "تكرار الباراسيتامول من منتجين مختلفين = خطر جرعة زائدة وتسمم كبد.", "اقرأ المكونات - أقصى حاجة 4 جرام في اليوم من كل المصادر."),
    ("decongestant_oral", "paracetamol", "major", "أدوية البرد المركبة فيها باراسيتامول أصلاً - خطر جرعة مضاعفة.", "متاخدش بانادول مع الكونجستال."),
]

# ---------------------------------------------------------------------------
# 7) علامات الخطر (Red Flags) - تحويل فوري
# ---------------------------------------------------------------------------
RED_FLAGS = [
    {
        "id": "chest_pain",
        "title": "ألم في الصدر",
        "keywords": ["الم في الصدر", "الم في صدري", "وجع في صدري", "صدري بيوجعني", "صدري واجعني", "chest pain", "ذبحه", "قلبي بيوجعني"],
        "action": "ألم الصدر ممكن يكون أزمة قلبية. اتصل بالإسعاف 123 فوراً، ولو مش عندك حساسية من الأسبرين امضغ قرص أسبرين 300 مجم وانت مستني.",
    },
    {
        "id": "breathing",
        "title": "ضيق شديد في التنفس",
        "keywords": ["ضيق تنفس", "ضيق في التنفس", "ضيق في النفس", "مش قادر اتنفس", "مش عارف اتنفس", "بنهج جامد", "اختناق", "شفايفي زرقا", "shortness of breath", "can't breathe", "cannot breathe"],
        "action": "ضيق التنفس الشديد حالة طارئة. اتصل بالإسعاف 123 أو روح أقرب طوارئ فوراً.",
    },
    {
        "id": "stroke",
        "title": "علامات جلطة في المخ",
        "keywords": ["وشي مايل", "بقي مايل", "تنميل في نص جسمي", "شلل", "مش قادر احرك ايدي", "مش قادر احرك رجلي", "تقل في الكلام", "صعوبه في الكلام", "stroke", "face drooping"],
        "action": "دي ممكن تكون علامات جلطة في المخ (FAST). كل دقيقة بتفرق! اتصل بالإسعاف 123 فوراً وسجل وقت بداية الأعراض.",
    },
    {
        "id": "thunderclap",
        "title": "صداع مفاجئ وشديد جداً",
        "keywords": ["اسوا صداع", "أسوأ صداع", "صداع مفاجئ جامد", "صداع زي الخبطه", "worst headache", "thunderclap"],
        "action": "الصداع المفاجئ الشديد جداً ممكن يكون نزيف في المخ. روح الطوارئ فوراً.",
    },
    {
        "id": "meningitis",
        "title": "تيبس في الرقبة مع حرارة",
        "keywords": ["تيبس في الرقبه", "رقبتي متخشبه", "مش قادر انزل راسي", "stiff neck", "طفح مش بيختفي"],
        "action": "الحرارة مع تيبس الرقبة ممكن تكون التهاب سحائي - حالة طارئة. روح الطوارئ فوراً.",
    },
    {
        "id": "bleeding",
        "title": "نزيف (دم في الترجيع أو البراز أو الكحة)",
        "keywords": ["ترجيع دم", "برجع دم", "دم في البراز", "براز اسود", "كحه بدم", "بكح دم", "دم في البول", "نزيف", "vomiting blood", "blood in stool", "black stool", "coughing blood"],
        "action": "وجود دم محتاج تقييم طبي عاجل. روح الطوارئ أو دكتور النهارده.",
    },
    {
        "id": "consciousness",
        "title": "إغماء أو تشنجات أو تشوش",
        "keywords": ["اغمى عليا", "اغماء", "فقدت الوعي", "تشنجات", "تشنج", "مش مركز خالص", "تايه", "faint", "seizure", "unconscious", "confused"],
        "action": "فقدان الوعي أو التشنجات حالة طارئة. اتصل بالإسعاف 123.",
    },
    {
        "id": "severe_abdomen",
        "title": "ألم شديد جداً في البطن",
        "keywords": ["الم شديد في بطني", "وجع جامد جدا في بطني", "بطني ناشفه", "الم في الجنب اليمين", "severe abdominal pain", "appendicitis", "زايده"],
        "action": "ألم البطن الشديد ممكن يكون زايدة أو حالة جراحية. روح الطوارئ فوراً ومتاخدش مسكنات قبل الكشف.",
    },
    {
        "id": "dehydration",
        "title": "جفاف شديد",
        "keywords": ["مفيش بول", "مش بعمل حمام خالص", "جفاف شديد", "عينه غايره", "severe dehydration", "no urine"],
        "action": "الجفاف الشديد محتاج محاليل في الوريد. روح الطوارئ.",
    },
    {
        "id": "anaphylaxis",
        "title": "تورم في الوش أو الشفايف (حساسية شديدة)",
        "keywords": ["وشي ورم", "شفايفي ورمت", "لساني ورم", "زوري بيقفل", "تورم في الوش", "anaphylaxis", "swollen lips", "swollen face"],
        "action": "ده ممكن يكون صدمة حساسية (Anaphylaxis). اتصل بالإسعاف 123 فوراً، ولو معاك قلم أدرينالين (EpiPen) استخدمه.",
    },
    {
        "id": "pregnancy_bleeding",
        "title": "نزيف أثناء الحمل",
        "keywords": ["نزيف وانا حامل", "حامل ونزلت دم", "bleeding pregnant"],
        "action": "النزيف أثناء الحمل محتاج دكتور نسا فوراً أو طوارئ.",
    },
    {
        "id": "suicide",
        "title": "أفكار إيذاء النفس",
        "keywords": ["انتحار", "عاوز اموت", "عايز اموت", "هموت نفسي", "اذي نفسي", "suicide", "kill myself"],
        "action": "إنت مش لوحدك وفي ناس عاوزة تساعدك. كلّم الخط الساخن للأمانة العامة للصحة النفسية 08008880700 (مجاني) أو 0220816831، أو روح أقرب طوارئ. ولو في خطر فوري اتصل بـ 123.",
    },
]

EMERGENCY_NUMBERS = {
    "الإسعاف": "123",
    "الطوارئ / النجدة": "122",
    "الخط الساخن للصحة النفسية": "08008880700",
}

# ---------------------------------------------------------------------------
# 8) التوسعة: حالات العضلات والعظام والجلد والفم والأذن وصحة المرأة والنوم
# ---------------------------------------------------------------------------
from .knowledge_extended import (  # noqa: E402
    EXTRA_CONDITIONS, EXTRA_DRUGS, EXTRA_INTERACTIONS, EXTRA_RED_FLAGS, EXTRA_SYMPTOMS, ORIGINAL_SOURCES,
)

SYMPTOMS.update(EXTRA_SYMPTOMS)
CONDITIONS.update(EXTRA_CONDITIONS)
DRUGS.update(EXTRA_DRUGS)
INTERACTIONS.extend(EXTRA_INTERACTIONS)
RED_FLAGS.extend(EXTRA_RED_FLAGS)
for _cid, _src in ORIGINAL_SOURCES.items():
    CONDITIONS[_cid].setdefault("source", _src)
