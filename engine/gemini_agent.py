"""
نفس الوكيل الذكي بس بعقل Google Gemini بدل Claude (مفتاح مجاني من Google AI Studio).

بيستخدم نفس الأدوات ونفس التعليمات ونفس ضوابط الأمان الموجودة في agent.py،
الفرق بس في طريقة الكلام مع الـ API (مكتبة google-genai).
"""
import re

from .agent import MAX_STEPS, SYSTEM_PROMPT, TOOL_LABELS, TOOLS, execute_tool, patient_context, summarize_result

DEFAULT_MODEL = "gemini-2.5-flash"

try:
    from google import genai
    from google.genai import errors, types
except ImportError:  # المكتبة مش متسطبة
    genai = None


def get_client(api_key: str):
    if genai is None or not api_key:
        return None
    return genai.Client(api_key=api_key)


def available_models(client) -> list:
    """
    الموديلات اللي المفتاح ده يقدر يستخدمها في المحادثة، مرتبة من الأحدث للأقدم،
    وموديلات Flash الأول (هي اللي عليها الخطة المجانية).
    """
    names = []
    try:
        for m in client.models.list():
            name = (m.name or "").removeprefix("models/")
            actions = m.supported_actions or []
            if not name.startswith("gemini-") or "generateContent" not in actions:
                continue
            if re.search(r"(image|tts|audio|live|embedding|vision|exp|computer|robotics)", name):
                continue
            names.append(name)
    except Exception:
        return [DEFAULT_MODEL]

    def rank(name):
        version = tuple(int(x) for x in re.findall(r"\d+", name.split("-")[1])) if "-" in name else (0,)
        return ("flash" in name and "lite" not in name, "preview" not in name, version)

    names = sorted(set(names), key=rank, reverse=True)
    return names or [DEFAULT_MODEL]


def _schema(schema: dict) -> dict:
    """نسخة من الـ JSON Schema من غير additionalProperties (Gemini مش محتاجها)."""
    clean = {k: v for k, v in schema.items() if k != "additionalProperties"}
    if "properties" in clean:
        clean["properties"] = {k: _schema(v) for k, v in clean["properties"].items()}
    if "items" in clean:
        clean["items"] = _schema(clean["items"])
    return clean


def _declarations():
    return [
        types.FunctionDeclaration(name=t["name"], description=t["description"],
                                  parameters_json_schema=_schema(t["input_schema"]))
        for t in TOOLS
    ]


def run_turn(client, history: list, user_text: str, profile: dict, chronic: list, on_tool=None,
             model: str = DEFAULT_MODEL) -> dict:
    """
    دور واحد من المحادثة بـ Gemini. history: قايمة types.Content (append-only).
    بيرجع {"text": رد شفاء, "events": [الأدوات اللي اتنفذت]} زي agent.run_turn بالظبط.
    """
    text_part = types.Part(text=f"{patient_context(profile, chronic)}\n\n{user_text}")
    if history and history[-1].role == "user":   # الدور اللي فات وقف بعد نتيجة أداة
        history[-1].parts.append(text_part)
    else:
        history.append(types.Content(role="user", parts=[text_part]))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=_declarations())],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    events = []
    for _ in range(MAX_STEPS):
        try:
            response = client.models.generate_content(model=model, contents=history, config=config)
        except errors.APIError as e:
            if e.code == 429:
                return {"text": "⏳ وصلت للحد المسموح في الخطة المجانية بتاعة Gemini. استنى دقيقة وجرب تاني، "
                                "أو استخدم تبويب المحرك المحلي.", "events": events}
            raise

        if not response.candidates or response.candidates[0].content is None:
            return {"text": "معلش، مقدرش أرد على الرسالة دي. لو عندك أعراض احكيلي عنها 🙏", "events": events}
        history.append(response.candidates[0].content)   # بيحفظ أجزاء التفكير (thought signatures) زي ما هي

        calls = response.function_calls or []
        if not calls:
            return {"text": (response.text or "").strip() or "معلش حصلت مشكلة، ممكن تعيد كلامك؟", "events": events}

        parts = []
        for call in calls:
            args = dict(call.args or {})
            try:
                result = execute_tool(call.name, args, profile, chronic)
            except Exception as e:
                result = {"error": f"{type(e).__name__}: {e}"}
            event = {"tool": call.name, "label": TOOL_LABELS.get(call.name, call.name),
                     "input": args, "summary": summarize_result(call.name, result)}
            events.append(event)
            if on_tool:
                on_tool(event)
            parts.append(types.Part(function_response=types.FunctionResponse(id=call.id, name=call.name, response=result)))
        history.append(types.Content(role="user", parts=parts))

    return {"text": "التفكير أخد وقت أطول من اللازم، ممكن توضحلي الأعراض أكتر؟", "events": events}
