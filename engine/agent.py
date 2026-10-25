"""
الوكيل الذكي (AI Agent) - شفاء بيدير المحادثة بنفسه ويقرر إمتى يدور وفين.

المعمارية: Claude (العقل) + أدوات (Tools):
  أدوات أونلاين  : search_pubmed / search_medlineplus / lookup_drug_label
  أدوات محلية    : check_red_flags / local_differential / check_drug_safety

حلقة الوكيل (Agentic Loop):
  1. المريض يكتب  ->  2. Claude يفكر ويطلب أداة  ->  3. البرنامج ينفذ الأداة ويرجع النتيجة
  4. Claude يكمل تفكير ويطلب أداة تانية أو يرد على المريض  ->  تتكرر لحد ما يرد.

الأمان (Guardrails) - حاجات Claude ميقدرش يتخطاها:
  - فحص علامات الخطر بيتعمل بالكود قبل ما الرسالة توصل لـ Claude أصلاً.
  - أي دواء لازم يعدي على check_drug_safety (موانع المريض + التداخلات مع أدويته) قبل ما يتقترح.
  - ممنوع أدوية الروشتة (مضادات حيوية، كورتيزون بالبق...) - تحويل للدكتور.
"""
import json
import re

from . import diagnosis, nlp, online_sources, safety
from .knowledge_base import CHRONIC_MEDS, CONDITIONS, DRUGS, PATIENT_CONDITIONS, SYMPTOMS

MODEL = "claude-opus-5-5"
MAX_STEPS = 12

SYSTEM_PROMPT = """أنت "شفاء"، صيدلي مصري ذكي وودود في تطبيق مشروع تخرج من كلية الصيدلة - جامعة القاهرة.
بتتكلم بالعامية المصرية البسيطة، وبتساعد المريض يفهم أعراضه ويعرف يتصرف إزاي بأمان.

## طريقة شغلك (زي الصيدلي الشاطر - WWHAM)
1. اسمع الشكوى. اسأل سؤال أو اتنين بس في كل رد (مش استجواب) لحد ما تعرف: الأعراض بالظبط، بقالها قد إيه، عمل إيه أو خد إيه.
2. استخدم الأدوات:
   - local_differential: أول ما يبقى عندك وصف للأعراض، ابعتله كل اللي المريض قاله لحد دلوقتي بالعربي. بيرجعلك تشخيص تفريقي احتمالي من قاعدة المعرفة المحلية (38 حالة) والسؤال الأذكى الجاي.
   - search_medlineplus: لو الحالة خارج القاعدة المحلية أو عاوز تتأكد من معلومة للمريض. ابحث بالإنجليزي.
   - search_pubmed: لما تحتاج دليل علمي (علاج، فعالية دواء، حالة مش شائعة). ابحث بكلمات إنجليزي قصيرة، ويفضل تضيف review أو guideline.
   - lookup_drug_label: النشرة الرسمية من FDA لأي دواء (موانع، تحذيرات، تداخلات).
   - check_drug_safety: **إجباري** قبل ما تقترح أي دواء. بيفحص سن المريض وأمراضه وأدويته المزمنة والتداخلات. لو قال ممنوع، متقترحوش.
3. لما توصل لتقييم: اكتب الرد النهائي بالشكل ده:
   - **التقييم المبدئي**: الحالة الأرجح ونسبة ثقتك، وحالة أو اتنين تانيين محتملين.
   - **العلاج المقترح بدون روشتة**: الدواء (الاسم العلمي + اسم تجاري مصري) والجرعة، بس الأدوية اللي عدت من check_drug_safety.
   - **نصايح**.
   - **روح للدكتور لو**.
   - **المصادر**: لينكات PubMed أو MedlinePlus اللي استخدمتها.

## قواعد أمان صارمة
- لو في أي علامة خطر (ألم صدر، ضيق تنفس شديد، أعراض جلطة، نزيف، إغماء، تيبس رقبة مع حرارة، ألم بطن شديد...) قول للمريض يتصل بالإسعاف 123 فوراً ومتكملش تشخيص.
- ممنوع تقترح أدوية روشتة (مضادات حيوية، كورتيزون بالبق، منومات، مسكنات أفيونية...). لو الحالة محتاجاها قول إنها محتاجة دكتور.
- متخترعش جرعات. الجرعات من نتيجة check_drug_safety أو نشرة FDA بس.
- خلي بالك من الحمل والرضاعة والأطفال وكبار السن والأمراض المزمنة الموجودة في ملف المريض.
- متقولش "تشخيص نهائي" - قول "تقييم مبدئي"، واختم بإن ده لا يغني عن الطبيب أو الصيدلي.
- لو السؤال مش طبي، رجّع المريض بلطف لموضوع الأعراض.
- خلي ردودك قصيرة ومنظمة، واستخدم إيموجي بسيط لو مناسب.
"""

TOOLS = [
    {
        "name": "check_red_flags",
        "description": "Rule-based emergency screen. Pass the patient's latest message (Arabic or English). Returns any red-flag symptoms that need emergency referral (call 123).",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Patient text to screen"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "local_differential",
        "description": (
            "Runs the local Bayesian diagnostic engine (38 common minor ailments seen in community pharmacy). "
            "Pass ALL symptom information the patient gave so far, in their own words (Egyptian Arabic is fine), "
            "including denied symptoms (e.g. 'مفيش سخونية'). Returns recognised symptoms, the top differential "
            "diagnoses with probabilities, the most informative next question, and the duration-based referral rules."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_text": {"type": "string", "description": "All the patient's symptom descriptions so far"},
                "duration_days": {"type": "integer", "description": "Symptom duration in days, or -1 if unknown"},
            },
            "required": ["patient_text", "duration_days"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "search_pubmed",
        "description": "Search PubMed (NIH/NLM, 36M+ biomedical papers). Use short English keywords; add 'review' or 'guideline' for higher-quality evidence. Returns titles, years, abstracts and links.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "English search query, e.g. 'plantar fasciitis treatment review'"},
                "max_results": {"type": "integer", "description": "1-8"},
            },
            "required": ["query", "max_results"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "search_medlineplus",
        "description": "Search MedlinePlus health topics (NIH/NLM, trusted patient-friendly encyclopedia). Use English keywords. Returns summaries and links.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "English keywords, e.g. 'varicose veins'"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "lookup_drug_label",
        "description": "Get the official U.S. FDA drug label (openFDA): indications, dosage, contraindications, warnings, pregnancy, interactions. Use the English generic name.",
        "input_schema": {
            "type": "object",
            "properties": {"generic_name": {"type": "string", "description": "e.g. 'diclofenac', 'loratadine'"}},
            "required": ["generic_name"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "check_drug_safety",
        "description": (
            "MANDATORY before recommending any medicine. Checks each drug against this patient's age, conditions "
            "(pregnancy, ulcer, kidney, hypertension...) and regular medicines (interactions, duplicate ingredients). "
            "Pass English generic or Egyptian brand names. Returns allowed/excluded with reasons and local dosing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"drugs": {"type": "array", "items": {"type": "string"}, "description": "Drug names"}},
            "required": ["drugs"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

TOOL_LABELS = {
    "check_red_flags": "🚨 فحص علامات الخطر",
    "local_differential": "🧠 المحرك الاحتمالي المحلي",
    "search_pubmed": "📚 بحث في PubMed",
    "search_medlineplus": "🏥 بحث في MedlinePlus",
    "lookup_drug_label": "💊 نشرة FDA",
    "check_drug_safety": "🛡️ فحص أمان الأدوية",
}


# ---------------------------------------------------------------------------
# تنفيذ الأدوات
# ---------------------------------------------------------------------------
def _find_drug(name: str):
    """يطابق اسم الدواء (علمي أو تجاري) بقاعدة البيانات: الأول تطابق كامل، وبعدين كل كلمات الاسم موجودة."""
    n = name.lower().strip()
    words = set(re.findall(r"[a-z0-9]+", n))
    for did, d in DRUGS.items():
        names = [did, d["generic"].lower()] + [b.strip().lower() for b in d["brands"].split(",")]
        if n in names:
            return did
    for did, d in DRUGS.items():
        haystack = set(re.findall(r"[a-z0-9]+", f"{did} {d['generic']} {d['brands']}".lower().replace("_", " ")))
        if words and words <= haystack:
            return did
    return None


def tool_local_differential(patient_text: str, duration_days: int, profile: dict) -> dict:
    known = nlp.extract_symptoms(patient_text)
    priors = diagnosis.adjusted_priors(profile)
    post = diagnosis.posterior(known, priors)
    top = list(post.items())[:5]
    q, gain = diagnosis.next_question(known, set(), priors)
    duration = None if duration_days is None or duration_days < 0 else duration_days
    top_id, top_p = top[0]
    return {
        "recognised_symptoms": {SYMPTOMS[s]["name"]: ("present" if v else "denied") for s, v in known.items()},
        "differential": [
            {"condition_id": c, "condition": diagnosis.condition_name(c), "probability": round(p, 3),
             "source": CONDITIONS.get(c, {}).get("source", "")}
            for c, p in top
        ],
        "most_informative_next_question": SYMPTOMS[q]["question"] if q else None,
        "suggested_otc_for_top": CONDITIONS[top_id]["drugs"] if top_id in CONDITIONS else [],
        "advice_for_top": CONDITIONS[top_id]["advice"] if top_id in CONDITIONS else [],
        "refer_if_for_top": CONDITIONS[top_id]["refer_if"] if top_id in CONDITIONS else [],
        "referral_reasons": safety.referral_reasons(top_id, profile, known, duration, top_p),
        "note": ("'unknown' means the complaint does not fit the 38 local conditions well: search MedlinePlus/PubMed "
                 "and be more cautious about referral." if top_id == diagnosis.UNKNOWN_ID else ""),
    }


def tool_check_drug_safety(drugs: list, profile: dict, chronic: list) -> dict:
    age = profile.get("age", 30)
    conds = set(profile.get("conditions", []))
    results, matched = [], []
    for name in drugs:
        did = _find_drug(name)
        if did is None:
            results.append({"drug": name, "status": "not_in_local_db",
                            "note": "Not in the local OTC database. If it is prescription-only, do not recommend it. "
                                    "Otherwise check lookup_drug_label and the patient's conditions yourself."})
            continue
        d = DRUGS[did]
        reasons = []
        if age < d.get("min_age", 0):
            reasons.append(f"below minimum age ({d['min_age']} years)")
        reasons += [f"contraindicated: {PATIENT_CONDITIONS[c]}" for c in d["avoid_if"] if c in conds]
        cautions = [f"use with caution: {PATIENT_CONDITIONS[c]}" for c in d["caution_if"] if c in conds]
        results.append({
            "drug": name, "matched": f"{d['generic']} ({d['brands']})",
            "status": "excluded" if reasons else "allowed", "reasons": reasons, "cautions": cautions,
            "dose": d["child_dose"] if age < 12 else d["adult_dose"], "notes": d["notes"],
        })
        if not reasons:
            matched.append(did)
    inter = safety.interactions_with_chronic(matched, chronic)
    inter += safety.check_interactions({d: DRUGS[d]["group"] for d in matched}, {d: DRUGS[d]["group"] for d in matched})
    return {
        "patient": {"age": age, "conditions": [PATIENT_CONDITIONS[c] for c in conds],
                    "regular_medicines": [CHRONIC_MEDS[m]["name"] for m in chronic]},
        "drugs": results,
        "interactions": [{"between": f"{safety.any_drug_name(i['a'])} + {safety.any_drug_name(i['b'])}",
                          "severity": i["severity"], "effect": i["effect"], "advice": i["advice"]} for i in inter],
    }


def execute_tool(name: str, args: dict, profile: dict, chronic: list) -> dict:
    if name == "check_red_flags":
        flags = nlp.detect_red_flags(args["text"])
        return {"red_flags": [{"title": f["title"], "action": f["action"]} for f in flags]}
    if name == "local_differential":
        return tool_local_differential(args["patient_text"], args.get("duration_days", -1), profile)
    if name == "search_pubmed":
        return online_sources.pubmed_search(args["query"], args.get("max_results", 5))
    if name == "search_medlineplus":
        return online_sources.medlineplus_search(args["query"])
    if name == "lookup_drug_label":
        return online_sources.openfda_label(args["generic_name"])
    if name == "check_drug_safety":
        return tool_check_drug_safety(args["drugs"], profile, chronic)
    return {"error": f"unknown tool {name}"}


def summarize_result(name: str, result: dict) -> str:
    """ملخص قصير بالعربي لنتيجة الأداة عشان يظهر للمستخدم في الواجهة."""
    if "error" in result:
        return f"⚠️ {result['error']}"
    if name in ("search_pubmed", "search_medlineplus"):
        items = result.get("results", [])
        if not items:
            return "مفيش نتايج"
        return "\n".join(f"- [{r['title']}]({r['url']})" + (f" ({r.get('year')})" if r.get("year") else "") for r in items)
    if name == "local_differential":
        return "\n".join(f"- {d['condition']}: {d['probability']:.0%}" for d in result["differential"][:3])
    if name == "check_drug_safety":
        lines = [f"- {d['drug']}: " + {"allowed": "✅ مسموح", "excluded": "🚫 ممنوع", "not_in_local_db": "❔ مش في القاعدة المحلية"}[d["status"]]
                 + (f" ({'، '.join(d['reasons'])})" if d.get("reasons") else "") for d in result["drugs"]]
        lines += [f"- ⚡ {i['between']} ({i['severity']})" for i in result["interactions"]]
        return "\n".join(lines)
    if name == "lookup_drug_label":
        return f"نشرة {result.get('drug')} — {', '.join(result.get('brand_names', [])) or 'FDA'}"
    if name == "check_red_flags":
        return "، ".join(f["title"] for f in result["red_flags"]) or "مفيش علامات خطر ✅"
    return ""


# ---------------------------------------------------------------------------
# حلقة الوكيل
# ---------------------------------------------------------------------------
def patient_context(profile: dict, chronic: list) -> str:
    sex = {"male": "ذكر", "female": "أنثى"}.get(profile.get("sex"), "غير محدد")
    conds = "، ".join(PATIENT_CONDITIONS[c] for c in profile.get("conditions", [])) or "لا يوجد"
    meds = "، ".join(CHRONIC_MEDS[m]["name"] for m in chronic) or "لا يوجد"
    return (f"[ملف المريض - من الشريط الجانبي: السن {profile.get('age')} سنة، {sex}، الوزن {profile.get('weight')} كجم، "
            f"أمراض/حالات خاصة: {conds}، أدوية منتظمة: {meds}]")


def run_turn(client, history: list, user_text: str, profile: dict, chronic: list, on_tool=None) -> dict:
    """
    دور واحد من المحادثة: بيضيف رسالة المريض للتاريخ ويشغل حلقة الوكيل لحد ما يرد.
    history: قايمة الرسايل بصيغة الـ API (بتتعدل في مكانها - append-only).
    بيرجع: {"text": رد شفاء, "events": [الأدوات اللي اتنفذت]}
    """
    text_block = {"type": "text", "text": f"{patient_context(profile, chronic)}\n\n{user_text}"}
    if history and history[-1]["role"] == "user":   # الدور اللي فات وقف بعد نتيجة أداة
        history[-1]["content"] = list(history[-1]["content"]) + [text_block]
    else:
        history.append({"role": "user", "content": [text_block]})
    events = []
    for _ in range(MAX_STEPS):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
            output_config={"effort": "medium"},
            cache_control={"type": "ephemeral"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            return {"text": "معلش، مقدرش أساعد في الطلب ده. لو عندك أعراض احكيلي عنها 🙏", "events": events}
        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return {"text": text or "معلش حصلت مشكلة، ممكن تعيد كلامك؟", "events": events}

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = execute_tool(block.name, block.input, profile, chronic)
                is_error = "error" in result
            except Exception as e:
                result, is_error = {"error": f"{type(e).__name__}: {e}"}, True
            event = {"tool": block.name, "label": TOOL_LABELS.get(block.name, block.name),
                     "input": block.input, "summary": summarize_result(block.name, result)}
            events.append(event)
            if on_tool:
                on_tool(event)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False), "is_error": is_error})
        history.append({"role": "user", "content": results})

    return {"text": "التفكير أخد وقت أطول من اللازم، ممكن توضحلي الأعراض أكتر؟", "events": events}
