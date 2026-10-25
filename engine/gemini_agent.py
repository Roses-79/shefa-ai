"""
نفس الوكيل الذكي بس بعقل Google Gemini بدل Claude (مفتاح مجاني من Google AI Studio).

بيستخدم نفس الأدوات ونفس التعليمات ونفس ضوابط الأمان الموجودة في agent.py،
الفرق بس في طريقة الكلام مع الـ API (مكتبة google-genai).
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .agent import MAX_STEPS, SYSTEM_PROMPT, TOOL_LABELS, TOOLS, execute_tool, patient_context, summarize_result

DEFAULT_MODEL = "gemini-flash-latest"
AUTO = "auto"            # اختيار تلقائي لأسرع موديل متاح دلوقتي
REQUEST_TIMEOUT_MS = 90_000
PROBE_TIMEOUT_MS = 15_000
TRANSIENT_CODES = {429, 500, 503, 504}
MAX_RATE_LIMIT_WAIT = 40  # ثانية

try:
    from google import genai
    from google.genai import errors, types
except ImportError:  # المكتبة مش متسطبة
    genai = None


def get_client(api_key: str):
    if genai is None or not api_key:
        return None
    # من غير إعادة محاولات مخفية: لما سيرفرات جوجل عليها ضغط، المكتبة كانت بتعيد المحاولة لوحدها
    # لدرجة إن الرد ياخد أكتر من دقيقتين. إحنا بنتعامل مع ده بنفسنا (اختيار موديل تاني).
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(
        timeout=REQUEST_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)))


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
            if re.search(r"(image|tts|audio|live|embedding|vision|exp|computer|robotics|transcribe|banana|omni|argon|customtools)", name):
                continue
            names.append(name)
    except Exception:
        return [DEFAULT_MODEL]

    def rank(name):
        version = tuple(int(x) for x in re.findall(r"\d+", name.split("-")[1])) if "-" in name else (0,)
        return ("flash" in name and "lite" not in name, "preview" not in name, version)

    names = sorted(set(names), key=rank, reverse=True)
    return names or [DEFAULT_MODEL]


def _probe(client, model: str) -> bool:
    """طلب صغير جداً عشان نعرف الموديل ده بيرد بسرعة دلوقتي ولا عليه ضغط."""
    try:
        r = client.models.generate_content(
            model=model, contents="ok",
            config=types.GenerateContentConfig(
                max_output_tokens=16, http_options=types.HttpOptions(timeout=PROBE_TIMEOUT_MS)))
        return bool(r.candidates)
    except Exception:
        return False


def pick_fast_model(client, models: list, max_probes: int = 6) -> str:
    """
    بيجرب أهم الموديلات (Flash الأول) في نفس الوقت، ويختار الأحدث من اللي ردوا.
    بياخد ثواني بس مرة واحدة في أول المحادثة.
    """
    candidates = [m for m in models if "lite" not in m][:max_probes] or models[:max_probes]
    with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
        futures = {pool.submit(_probe, client, m): m for m in candidates}
        ok = {futures[f] for f in as_completed(futures) if f.result()}
    for m in candidates:                 # نفس ترتيب الأولوية (الأحدث الأول)
        if m in ok:
            return m
    for m in models:                     # لو كله عليه ضغط: نجرب الباقي (زي lite) واحد واحد
        if m not in candidates and _probe(client, m):
            return m
    return candidates[0] if candidates else DEFAULT_MODEL


def _schema(schema: dict) -> dict:
    """نسخة من الـ JSON Schema من غير additionalProperties (Gemini مش محتاجها)."""
    clean = {k: v for k, v in schema.items() if k != "additionalProperties"}
    if "properties" in clean:
        clean["properties"] = {k: _schema(v) for k, v in clean["properties"].items()}
    if "items" in clean:
        clean["items"] = _schema(clean["items"])
    return clean


def _declarations():
    # فحص علامات الخطر بيتعمل بالكود قبل الموديل، فمش محتاجين نصرف عليه طلب من الخطة المجانية
    return [
        types.FunctionDeclaration(name=t["name"], description=t["description"],
                                  parameters_json_schema=_schema(t["input_schema"]))
        for t in TOOLS if t["name"] != "check_red_flags"
    ]


def _retry_delay(error) -> float:
    """عدد الثواني اللي جوجل طالبة نستناها قبل ما نعيد الطلب (من رسالة الخطأ 429)."""
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", str(error))
    return float(m.group(1)) + 1 if m else 20.0


def run_turn(client, history: list, user_text: str, profile: dict, chronic: list, on_tool=None,
             model: str = DEFAULT_MODEL, on_wait=None) -> dict:
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
        response = None
        for attempt in range(2):         # محاولة تانية واحدة بس لو السيرفر عليه ضغط
            try:
                response = client.models.generate_content(model=model, contents=history, config=config)
                break
            except errors.APIError as e:
                wait = _retry_delay(e)
                if e.code == 429 and attempt == 0 and wait <= MAX_RATE_LIMIT_WAIT:
                    # الخطة المجانية ليها حد في الدقيقة: نستنى الوقت اللي جوجل قالت عليه ونكمل لوحدنا
                    if on_wait:
                        on_wait(wait)
                    time.sleep(wait)
                    continue
                if e.code not in TRANSIENT_CODES or attempt == 1:
                    if e.code == 429:
                        return {"text": "⏳ وصلت للحد المسموح في الخطة المجانية بتاعة Gemini. استنى دقيقة وابعت "
                                        "رسالتك تاني، أو استخدم تبويب المحرك المحلي.", "events": events}
                    if e.code in TRANSIENT_CODES:
                        return {"text": "⏳ سيرفرات جوجل عليها ضغط دلوقتي. ابعت رسالتك تاني، أو دوس "
                                        "\"محادثة جديدة\" عشان أختار موديل أسرع.", "events": events}
                    raise
            except Exception as e:      # انتهاء المهلة من غير رد من السيرفر
                if "timeout" not in type(e).__name__.lower() or attempt == 1:
                    if "timeout" in type(e).__name__.lower():
                        return {"text": "⏳ الرد أخد وقت طويل. ابعت رسالتك تاني، أو دوس \"محادثة جديدة\" عشان "
                                        "أختار موديل أسرع.", "events": events}
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
