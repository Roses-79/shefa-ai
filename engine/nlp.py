"""
معالجة اللغة الطبيعية (NLP) البسيطة للعربي (عامية مصرية + فصحى) والإنجليزي.

الخطوات:
  1. Normalization : توحيد أشكال الحروف (أ إ آ -> ا ، ة -> ه ، ى -> ي) وحذف التشكيل.
  2. Matching      : البحث عن مرادفات كل عرض في الكلام.
  3. Negation      : لو قبل العرض كلمة نفي (مفيش / مش / بدون / no ...) يبقى العرض "مش موجود".
  4. Extraction    : استخراج مدة الأعراض بالأيام ودرجة الحرارة لو مذكورة.
"""
import re

from .knowledge_base import RED_FLAGS, SYMPTOMS

_DIACRITICS = re.compile(r"[ؗ-ًؚ-ْٰـ]")  # تشكيل + تطويل

NEGATION_WORDS = {
    "مفيش", "مافيش", "مش", "مو", "ماعنديش", "معنديش", "ماعندهوش", "معندوش", "بدون", "غير",
    "لا", "ولا", "ليس", "لم", "لا يوجد", "مابقاش", "no", "not", "without", "dont", "don't", "never", "denies",
}

ARABIC_NUMBERS = {
    "يوم": 1, "يومين": 2, "اسبوع": 7, "اسبوعين": 14, "شهر": 30, "اسبوعين ونص": 17,
    "تلات": 3, "تلت": 3, "ثلاث": 3, "اربع": 4, "خمس": 5, "ست": 6, "سبع": 7, "عشر": 10,
}


def normalize(text: str) -> str:
    """توحيد شكل النص العربي عشان المطابقة تبقى أدق."""
    text = text.lower()
    text = _DIACRITICS.sub("", text)
    text = re.sub("[إأآٱ]", "ا", text)
    text = text.replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    text = re.sub("[٠-٩]", lambda m: str("٠١٢٣٤٥٦٧٨٩".index(m.group())), text)  # أرقام عربية -> إنجليزي
    text = re.sub(r"[^\w\s.°]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_english(word: str) -> bool:
    return bool(re.match(r"^[a-z0-9' ]+$", word))


def _find(text: str, synonym: str):
    """يرجع مكان أول ظهور للمرادف في النص (أو None)."""
    syn = normalize(synonym)
    if not syn:
        return None
    if _is_english(syn):
        pattern = r"\b" + re.escape(syn) + r"\b"
    elif len(syn) <= 3:
        # الكلمات القصيرة لازم تكون كلمة مستقلة عشان ميحصلش تطابق غلط
        pattern = r"(?:^|\s)(?:و|ف|ب|ال|وال|بال)?" + re.escape(syn) + r"(?=\s|$)"
    else:
        pattern = re.escape(syn)
    m = re.search(pattern, text)
    return m.start() if m else None


def _negated(text: str, position: int) -> bool:
    """هل في كلمة نفي في آخر كلمتين قبل العرض؟"""
    before = text[:position].split()[-2:]
    for word in before:
        word = word[1:] if word.startswith("و") and len(word) > 2 else word  # "ومفيش" -> "مفيش"
        if word in NEGATION_WORDS:
            return True
    return False


def extract_symptoms(text: str) -> dict:
    """
    يرجع dict: {symptom_id: True/False}
    True  = العرض موجود
    False = المريض نفى العرض صراحة
    """
    clean = normalize(text)
    found = {}
    for sid, info in SYMPTOMS.items():
        for syn in info["synonyms"]:
            pos = _find(clean, syn)
            if pos is not None:
                found[sid] = not _negated(clean, pos)
                break

    # درجة الحرارة لو مكتوبة كرقم: "حرارتي 39" أو "38.5 درجة"
    temp = extract_temperature(clean)
    if temp is not None:
        found["fever"] = temp >= 38
        found["high_fever"] = temp >= 39

    # لو المريض قال كحة ناشفة أو ببلغم يبقى عنده كحة أكيد
    if found.get("cough_dry") or found.get("cough_productive"):
        found["cough"] = True
    if found.get("one_sided_headache") or found.get("band_headache"):
        found["headache"] = True
    if found.get("high_fever"):
        found["fever"] = True
    return found


def extract_temperature(clean_text: str):
    patterns = [
        r"(?:حراره|حرارتي|سخونيه|temp|temperature|fever)\D{0,12}?(3[5-9]|4[0-2])(?:[.,](\d))?",
        r"(3[5-9]|4[0-2])(?:[.,](\d))?\s*(?:درجه|درجات|°|c\b)",
    ]
    for p in patterns:
        m = re.search(p, clean_text)
        if m:
            value = float(m.group(1))
            if m.group(2):
                value += int(m.group(2)) / 10
            return value
    return None


def extract_duration_days(text: str):
    """يحاول يعرف الأعراض بقالها قد إيه بالأيام."""
    clean = normalize(text)
    m = re.search(r"(\d+)\s*(يوم|ايام|days?|اسبوع|اسابيع|weeks?|شهر|شهور|months?)", clean)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith(("اسبوع", "اسابيع", "week")):
            return n * 7
        if unit.startswith(("شهر", "شهور", "month")):
            return n * 30
        return n
    for word in ["اسبوعين", "يومين", "اسبوع", "شهر", "امبارح", "النهارده", "تلات ايام", "ثلاث ايام", "خمس ايام", "اربع ايام"]:
        if word in clean:
            return {"اسبوعين": 14, "يومين": 2, "اسبوع": 7, "شهر": 30, "امبارح": 1, "النهارده": 0,
                    "تلات ايام": 3, "ثلاث ايام": 3, "خمس ايام": 5, "اربع ايام": 4}[word]
    return None


def detect_red_flags(text: str) -> list:
    """يرجع قايمة بعلامات الخطر اللي اتذكرت في الكلام (مع تجاهل المنفية)."""
    clean = normalize(text)
    hits = []
    for flag in RED_FLAGS:
        for kw in flag["keywords"]:
            pos = _find(clean, kw)
            if pos is not None and not _negated(clean, pos):
                hits.append(flag)
                break
    return hits


def parse_yes_no(text: str):
    """تفسير رد المريض على سؤال نعم/لا. يرجع True / False / None (مش متأكد)."""
    clean = normalize(text)
    yes = {"اه", "ايوه", "ايوا", "نعم", "اكيد", "صح", "طبعا", "yes", "y", "yeah", "yep", "ok", "عندي", "ايه", "اها"}
    no = {"لا", "لأ", "لاء", "مفيش", "مش", "no", "n", "nope", "لاا", "ابدا", "معنديش", "ماعنديش"}
    words = clean.split()
    if not words:
        return None
    if words[0] in no or clean in no:
        return False
    if words[0] in yes or clean in yes:
        return True
    return None
