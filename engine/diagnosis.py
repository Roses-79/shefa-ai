"""
محرك التشخيص الاحتمالي (Bayesian Diagnostic Engine).

الفكرة باختصار:
  P(Disease | Symptoms) ∝ P(Disease) × Π P(Symptom_i | Disease)

  - لكل حالة بنبدأ باحتمالها المبدئي (Prior).
  - كل عرض موجود بنضرب في احتمال وجوده مع الحالة دي.
  - كل عرض المريض نفاه بنضرب في (1 - احتمال وجوده).
  - في الآخر بنعمل Normalization عشان المجموع يبقى 100%.

ده اسمه Naive Bayes Classifier، وبنستخدم اللوغاريتمات عشان نتجنب
إن الأرقام الصغيرة جداً تتصفّر في الكمبيوتر (Numerical underflow).

اختيار السؤال الجاي بيتم بـ "كسب المعلومات" (Information Gain):
بنسأل عن العرض اللي إجابته (نعم أو لا) هتقلل عدم اليقين (Entropy) أكتر حاجة،
وده نفس منطق الدكتور الشاطر اللي بيسأل السؤال الصح مش كل الأسئلة.
"""
import math

from .knowledge_base import CONDITIONS, LEAK_PROBABILITY, SYMPTOMS, UNKNOWN_CONDITION

UNKNOWN_ID = "unknown"
CONFIDENCE_THRESHOLD = 0.80   # لو أعلى احتمال وصل للرقم ده نوقف الأسئلة
MAX_QUESTIONS = 7             # أقصى عدد أسئلة متابعة
MIN_INFO_GAIN = 0.03          # لو مفيش سؤال هيضيف معلومة مفيدة نوقف


def adjusted_priors(profile: dict) -> dict:
    """تعديل الاحتمالات المبدئية حسب بيانات المريض (السن والنوع)."""
    sex = profile.get("sex", "unknown")
    age = profile.get("age", 30)
    priors = {cid: c["prior"] for cid, c in CONDITIONS.items()}
    priors[UNKNOWN_ID] = UNKNOWN_CONDITION["prior"]

    if sex == "male" or age < 10 or age > 55:
        priors["dysmenorrhea"] = 0.0
    if sex == "female":
        priors["uti"] *= 2.5          # التهاب المثانة أشهر بكتير في الستات
        priors["dysmenorrhea"] *= 1.5
    elif sex == "male":
        priors["uti"] *= 0.3
    if age < 12:
        priors["migraine"] *= 0.5
        priors["gerd"] *= 0.3
        priors["gastroenteritis"] *= 1.5
    if age > 60:
        priors["influenza"] *= 1.2
        priors["constipation"] *= 1.5
        priors[UNKNOWN_ID] *= 2       # كبار السن الأعراض عندهم أقل نمطية
    return priors


def _likelihood(cid: str, sid: str) -> float:
    if cid == UNKNOWN_ID:
        return UNKNOWN_CONDITION["default_likelihood"]
    return CONDITIONS[cid]["likelihoods"].get(sid, LEAK_PROBABILITY)


def posterior(known: dict, priors: dict) -> dict:
    """حساب الاحتمال البعدي لكل حالة بناءً على الأعراض المعروفة (موجودة أو منفية)."""
    log_scores = {}
    for cid, prior in priors.items():
        if prior <= 0:
            continue
        score = math.log(prior)
        for sid, present in known.items():
            if present is None:       # "مش متأكد" -> مش بنحسبها
                continue
            p = _likelihood(cid, sid)
            score += math.log(p if present else (1 - p))
        log_scores[cid] = score

    # Softmax (log-sum-exp) للتحويل لاحتمالات مجموعها 1
    top = max(log_scores.values())
    exp_scores = {cid: math.exp(s - top) for cid, s in log_scores.items()}
    total = sum(exp_scores.values())
    return dict(sorted(((cid, v / total) for cid, v in exp_scores.items()), key=lambda x: -x[1]))


def entropy(dist: dict) -> float:
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


def information_gain(sid: str, known: dict, priors: dict, current: dict) -> float:
    """كمية المعلومات المتوقعة لو سألنا عن العرض ده."""
    p_yes = sum(p * _likelihood(cid, sid) for cid, p in current.items())
    p_yes = min(max(p_yes, 1e-6), 1 - 1e-6)
    post_yes = posterior({**known, sid: True}, priors)
    post_no = posterior({**known, sid: False}, priors)
    expected_h = p_yes * entropy(post_yes) + (1 - p_yes) * entropy(post_no)
    return entropy(current) - expected_h


def next_question(known: dict, asked: set, priors: dict):
    """
    يرجع (symptom_id, info_gain) للسؤال الأفضل، أو (None, 0) لو مفيش داعي لأسئلة تانية.
    بنحصر البحث في الأعراض المرتبطة بأعلى 5 حالات عشان الأسئلة تبقى منطقية.
    """
    current = posterior(known, priors)
    top_conditions = [cid for cid in list(current)[:5] if cid != UNKNOWN_ID]
    candidates = set()
    for cid in top_conditions:
        candidates.update(CONDITIONS[cid]["likelihoods"].keys())
    candidates -= set(known) | asked

    best, best_gain = None, 0.0
    for sid in sorted(candidates):
        if sid not in SYMPTOMS:
            continue
        gain = information_gain(sid, known, priors, current)
        if gain > best_gain:
            best, best_gain = sid, gain
    if best_gain < MIN_INFO_GAIN:
        return None, 0.0
    return best, best_gain


def should_stop(known: dict, asked: set, priors: dict) -> bool:
    current = posterior(known, priors)
    top_p = next(iter(current.values()))
    return top_p >= CONFIDENCE_THRESHOLD or len(asked) >= MAX_QUESTIONS


def confidence_label(p: float) -> str:
    if p >= 0.80:
        return "ثقة عالية"
    if p >= 0.55:
        return "ثقة متوسطة"
    return "ثقة منخفضة"


def condition_name(cid: str) -> str:
    return UNKNOWN_CONDITION["name"] if cid == UNKNOWN_ID else CONDITIONS[cid]["name"]


def explain(cid: str, known: dict) -> list:
    """
    Explainable AI: يرجع الأعراض اللي أثّرت أكتر في الحكم على الحالة دي
    (Likelihood ratio = احتمال العرض مع الحالة ÷ احتماله مع باقي الحالات في المتوسط).
    """
    if cid == UNKNOWN_ID:
        return []
    reasons = []
    others = [c for c in CONDITIONS if c != cid]
    for sid, present in known.items():
        if present is None:
            continue
        p_c = _likelihood(cid, sid)
        p_other = sum(_likelihood(o, sid) for o in others) / len(others)
        if present:
            lr = p_c / p_other
        else:
            lr = (1 - p_c) / (1 - p_other)
        reasons.append((sid, present, lr))
    reasons.sort(key=lambda r: -abs(math.log(r[2])))
    return reasons[:4]
