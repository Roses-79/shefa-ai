"""
طبقة الأمان الدوائي (Pharmaceutical Safety Layer) - دي قلب دور الصيدلي في المشروع.

  1. filter_drugs        : استبعاد الأدوية الممنوعة على المريض (حمل، قرحة، كلى، سن...) مع ذكر السبب.
  2. check_interactions  : فحص التداخلات بين الأدوية المقترحة وأدوية المريض المزمنة.
  3. referral_reasons    : قواعد التحويل للدكتور (مدة الأعراض، فئات خاصة...).
  4. pediatric_dose      : حساب جرعات الأطفال بالوزن وتحويلها لمللي من الشراب.
"""
from .knowledge_base import CHRONIC_MEDS, CONDITIONS, DRUGS, INTERACTIONS, PATIENT_CONDITIONS

SEVERITY_AR = {"major": "خطير", "moderate": "متوسط", "minor": "بسيط"}
SEVERITY_ORDER = {"major": 0, "moderate": 1, "minor": 2}


def filter_drugs(condition_id: str, profile: dict, known: dict) -> tuple:
    """
    يرجع (allowed, excluded)
      allowed : [(drug_id, [تحذيرات])]
      excluded: [(drug_id, [أسباب الاستبعاد])]
    """
    if condition_id not in CONDITIONS:
        return [], []
    age = profile.get("age", 30)
    patient_conds = set(profile.get("conditions", []))
    if known.get("fever"):
        patient_conds.add("fever_present")
    if known.get("diarrhea") or known.get("vomiting"):
        patient_conds.add("dehydration_risk")

    allowed, excluded = [], []
    for did in CONDITIONS[condition_id]["drugs"]:
        drug = DRUGS[did]
        reasons, warnings = [], []
        if age < drug.get("min_age", 0):
            reasons.append(f"غير مناسب لسن أقل من {_age_text(drug['min_age'])}")
        if age > drug.get("max_age", 200):
            reasons.append("مخصص للأطفال")
        for c in drug["avoid_if"]:
            if c in patient_conds:
                reasons.append(f"ممنوع مع: {_cond_name(c)}")
        if drug["group"] == "nsaid" and "dehydration_risk" in patient_conds:
            warnings.append("انتبه: مع الإسهال أو الترجيع الكتير الأفضل باراسيتامول لحماية الكلى")
        for c in drug["caution_if"]:
            if c in patient_conds:
                warnings.append(f"يُستخدم بحذر وبعد استشارة مع: {_cond_name(c)}")
        if reasons:
            excluded.append((did, reasons))
        else:
            allowed.append((did, warnings))
    return allowed, excluded


def check_interactions(drug_groups_a: dict, drug_groups_b: dict) -> list:
    """
    فحص التداخلات بين مجموعتين من الأدوية.
    المدخلات: {id: group}  - المخرجات: قايمة مرتبة بالخطورة.
    """
    results, seen = [], set()
    for ida, ga in drug_groups_a.items():
        for idb, gb in drug_groups_b.items():
            if ida == idb:
                continue
            key = tuple(sorted([ida, idb]))
            if key in seen:
                continue
            match = _match(_groups(ida, ga), _groups(idb, gb))
            if match:
                seen.add(key)
                severity, effect, advice = match
                results.append({
                    "a": ida, "b": idb, "severity": severity,
                    "severity_ar": SEVERITY_AR[severity], "effect": effect, "advice": advice,
                })
    return sorted(results, key=lambda r: SEVERITY_ORDER[r["severity"]])


def _groups(drug_id: str, group: str) -> set:
    """المجموعات الدوائية للدواء (الأدوية المركبة ليها أكتر من مجموعة، زي الكونجستال فيه باراسيتامول)."""
    return {group, *DRUGS.get(drug_id, {}).get("also", [])}


def _match(groups_a: set, groups_b: set):
    """أخطر تداخل بين مجموعتين من المجموعات الدوائية."""
    best = None
    for g1, g2, severity, effect, advice in INTERACTIONS:
        if (g1 in groups_a and g2 in groups_b) or (g2 in groups_a and g1 in groups_b):
            if best is None or SEVERITY_ORDER[severity] < SEVERITY_ORDER[best[0]]:
                best = (severity, effect, advice)
    return best


def interactions_with_chronic(drug_ids: list, chronic_ids: list) -> list:
    a = {d: DRUGS[d]["group"] for d in drug_ids}
    b = {m: CHRONIC_MEDS[m]["group"] for m in chronic_ids}
    return check_interactions(a, b)


def any_drug_name(did: str) -> str:
    if did in DRUGS:
        return f"{DRUGS[did]['generic']} ({DRUGS[did]['brands'].split(',')[0]})"
    if did in CHRONIC_MEDS:
        return CHRONIC_MEDS[did]["name"]
    return did


def referral_reasons(condition_id: str, profile: dict, known: dict, duration_days, top_probability: float) -> list:
    """قواعد التحويل للطبيب - لو رجعت أي سبب يبقى لازم دكتور."""
    reasons = []
    age = profile.get("age", 30)
    conds = set(profile.get("conditions", []))
    cond = CONDITIONS.get(condition_id)

    if cond is None:
        reasons.append("الأعراض مش واضحة كفاية أو خارج نطاق الحالات البسيطة اللي النظام بيتعامل معاها.")
    else:
        if cond.get("always_refer"):
            reasons.append("الحالة دي غالباً محتاجة علاج بروشتة (مضاد حيوي) - لازم كشف.")
        if duration_days is not None and duration_days > cond["max_days"]:
            reasons.append(f"الأعراض مكملة {duration_days} يوم، وده أكتر من المتوقع للحالة دي ({cond['max_days']} أيام).")
        if condition_id == "uti" and (profile.get("sex") == "male" or "pregnancy" in conds or age < 16):
            reasons.append("التهاب البول عند الرجالة والحوامل والأطفال بيعتبر حالة معقدة ولازم دكتور فوراً.")
        if condition_id == "influenza" and (age >= 65 or "pregnancy" in conds or conds & {"heart_disease", "asthma", "diabetes", "kidney"}):
            reasons.append("من الفئات الأكثر عرضة لمضاعفات الإنفلونزا - كلّم دكتور خلال 48 ساعة.")
        if condition_id == "gastroenteritis" and (age < 0.5 or age > 75):
            reasons.append("الإسهال عند الرضع أقل من 6 شهور وكبار السن خطر جفاف عالي - لازم دكتور.")

    if top_probability < 0.55:
        reasons.append("النظام مش واثق كفاية من التشخيص (أقل من 55%) - الأفضل تقييم طبي.")
    if known.get("high_fever") and age < 0.25:
        reasons.append("أي حرارة في رضيع أقل من 3 شهور حالة طارئة.")
    elif known.get("fever") and age < 0.25:
        reasons.append("أي حرارة في رضيع أقل من 3 شهور حالة طارئة.")
    if known.get("high_fever") and duration_days and duration_days >= 3:
        reasons.append("حرارة عالية بقالها 3 أيام أو أكتر.")
    if "pregnancy" in conds:
        reasons.append("أثناء الحمل: أي دواء لازم يتاخد بعد استشارة دكتور النسا.")
    return reasons


def pediatric_dose(drug: str, weight_kg: float, age_years: float, concentration_mg_per_5ml: float) -> dict:
    """
    حساب جرعة الطفل بالوزن.
      Paracetamol: 15 مجم/كجم/جرعة كل 4-6 ساعات (أقصى 60 مجم/كجم/يوم، و 1000 مجم/جرعة)
      Ibuprofen  : 10 مجم/كجم/جرعة كل 6-8 ساعات (من 6 شهور، أقصى 30 مجم/كجم/يوم، و 400 مجم/جرعة)
    """
    rules = {
        "paracetamol": {"mg_per_kg": 15, "max_dose": 1000, "max_daily_per_kg": 60, "max_daily": 4000,
                        "interval": "كل 4-6 ساعات", "doses_per_day": 4, "min_age": 0.25},
        "ibuprofen": {"mg_per_kg": 10, "max_dose": 400, "max_daily_per_kg": 30, "max_daily": 1200,
                      "interval": "كل 6-8 ساعات بعد الأكل", "doses_per_day": 3, "min_age": 0.5},
    }
    r = rules[drug]
    if weight_kg <= 0 or concentration_mg_per_5ml <= 0:
        return {"ok": False, "message": "ادخل وزن وتركيز صحيح."}
    if age_years < r["min_age"]:
        return {"ok": False, "message": f"غير مناسب لسن أقل من {_age_text(r['min_age'])} - لازم دكتور أطفال."}
    dose_mg = min(weight_kg * r["mg_per_kg"], r["max_dose"])
    dose_ml = dose_mg * 5 / concentration_mg_per_5ml
    daily_max_mg = min(weight_kg * r["max_daily_per_kg"], r["max_daily"])
    return {
        "ok": True,
        "dose_mg": round(dose_mg, 1),
        "dose_ml": round(dose_ml, 1),
        "interval": r["interval"],
        "max_doses": r["doses_per_day"],
        "daily_max_mg": round(daily_max_mg),
        "daily_max_ml": round(daily_max_mg * 5 / concentration_mg_per_5ml, 1),
    }


def _cond_name(c: str) -> str:
    extra = {"fever_present": "وجود حرارة", "dehydration_risk": "خطر الجفاف"}
    return PATIENT_CONDITIONS.get(c, extra.get(c, c))


def _age_text(years: float) -> str:
    if years < 1:
        return f"{round(years * 12)} شهور"
    return f"{years:g} سنين" if years < 11 else f"{years:g} سنة"
