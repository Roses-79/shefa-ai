"""
طبقة الذكاء الاصطناعي التوليدي (اختيارية) باستخدام Claude من Anthropic.

النظام شغال 100% من غيرها (Offline) - لكن لو حطيت API key بتضيف حاجتين:
  1. فهم أعمق للكلام الحر: لو المريض كتب بطريقة غريبة، Claude بيحوّل كلامه لأعراض من القايمة.
  2. شرح ودود للنتيجة بالعامية المصرية.

مبدأ الأمان (Guardrails): Claude مش بيشخّص ومش بيقترح أدوية من عنده.
التشخيص والأدوية بيطلعوا من المحرك الاحتمالي وطبقة الأمان بس، وClaude بيصيغ الكلام فقط.
"""
import json
import os

from .knowledge_base import SYMPTOMS

MODEL = "claude-opus-5-5"

try:
    import anthropic
except ImportError:  # المكتبة مش متسطبة -> الوضع الأوفلاين
    anthropic = None


def get_client(api_key: str = None):
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if anthropic is None or not key:
        return None
    return anthropic.Anthropic(api_key=key)


def _call(client, system: str, user: str, max_tokens: int = 2000, schema: dict = None) -> str:
    output_config = {"effort": "low"}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config=output_config,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return ""
    return "".join(b.text for b in response.content if b.type == "text")


def ai_extract_symptoms(client, text: str) -> dict:
    """يحوّل كلام المريض الحر لأعراض من القايمة المعروفة (Structured Output)."""
    catalog = "\n".join(f"- {sid}: {info['name']}" for sid, info in SYMPTOMS.items())
    system = (
        "You map a patient's free-text complaint (Egyptian Arabic, Arabic or English) to a fixed symptom catalog. "
        "Only use ids from the catalog. Mark a symptom present=true if the patient reports it, present=false only if "
        "they explicitly deny it. Do not guess symptoms that were not mentioned.\n\nCatalog:\n" + catalog
    )
    schema = {
        "type": "object",
        "properties": {
            "symptoms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "enum": list(SYMPTOMS)},
                        "present": {"type": "boolean"},
                    },
                    "required": ["id", "present"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["symptoms"],
        "additionalProperties": False,
    }
    try:
        raw = _call(client, system, text, max_tokens=1500, schema=schema)
        data = json.loads(raw) if raw else {"symptoms": []}
        return {s["id"]: s["present"] for s in data["symptoms"] if s["id"] in SYMPTOMS}
    except Exception:
        return {}


def ai_explain(client, summary: str) -> str:
    """صياغة شرح ودود للمريض من نتيجة المحرك (من غير ما يضيف تشخيص أو دواء جديد)."""
    system = (
        "أنت صيدلي مصري ودود في تطبيق اسمه شفاء AI. هيوصلك ملخص نتيجة نظام تشخيص مبدئي. "
        "اكتب للمريض شرح قصير (5-7 سطور) بالعامية المصرية البسيطة: طمّنه، اشرح الحالة ببساطة، "
        "وأكّد على أهم نصيحة وعلى إمتى لازم يروح للدكتور. "
        "ممنوع تضيف أي تشخيص أو دواء أو جرعة مش موجودة في الملخص. "
        "اختم بجملة إن ده تقييم مبدئي ولا يغني عن الطبيب."
    )
    try:
        return _call(client, system, summary, max_tokens=2000).strip()
    except Exception:
        return ""
