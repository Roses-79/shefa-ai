"""
🩺 شفاء AI — المساعد الصيدلي الذكي للتقييم المبدئي للأعراض
مشروع تخرج - كلية الصيدلة - جامعة القاهرة

للتشغيل:  streamlit run app.py
"""
import streamlit as st

from engine import agent, ai_assistant, diagnosis, gemini_agent, nlp, safety
from engine.knowledge_base import (
    CHRONIC_MEDS, CONDITIONS, DRUGS, EMERGENCY_NUMBERS, INTERACTIONS, PATIENT_CONDITIONS, RED_FLAGS, SYMPTOMS,
)
from engine.report import build_report

st.set_page_config(page_title="شفاء AI", page_icon="🩺", layout="wide")

# ---------------------------------------------------------------------------
# التصميم (CSS) - اتجاه من اليمين للشمال + خط Cairo
# ---------------------------------------------------------------------------
st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea, label, p, li, h1, h2, h3, h4 {
    font-family: 'Cairo', sans-serif !important;
}
.main .block-container, section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
.stChatMessage { direction: rtl; text-align: right; }
.hero {
    background: linear-gradient(135deg, #0b7a75 0%, #14a098 55%, #5fd3bc 100%);
    color: white; padding: 22px 28px; border-radius: 18px; margin-bottom: 18px;
    box-shadow: 0 8px 24px rgba(11,122,117,.25);
}
.hero h1 { color: white; margin: 0; font-size: 34px; font-weight: 800; }
.hero p { margin: 4px 0 0; opacity: .95; font-size: 16px; }
.card {
    background: var(--secondary-background-color); border-radius: 14px; padding: 14px 18px;
    margin: 8px 0; border-right: 5px solid #14a098;
}
.card.red { border-right-color: #e53935; background: rgba(229,57,53,.08); }
.card.amber { border-right-color: #ffb300; background: rgba(255,179,0,.08); }
.card.green { border-right-color: #43a047; background: rgba(67,160,71,.08); }
.pill { display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; margin-left: 6px;
        background: #e0f2f1; color: #0b7a75; font-weight: 600; }
.pill.red { background:#ffebee; color:#c62828; } .pill.amber { background:#fff8e1; color:#b26a00; }
.big-dose { font-size: 44px; font-weight: 800; color: #0b7a75; }
.small { font-size: 13px; opacity: .75; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# حالة الجلسة
# ---------------------------------------------------------------------------
GREETING = (
    "أهلاً بيك! أنا **شفاء** 👋 مساعدك الصيدلي الذكي.\n\n"
    "احكيلي بتحس بإيه بكلامك العادي، مثلاً: *\"عندي رشح وعطس وزوري بيوجعني من يومين\"*.\n\n"
    "هسألك كام سؤال بسيط، وبعدها هقولك التقييم المبدئي والعلاج المناسب ليك وإمتى لازم تروح للدكتور."
)


def reset_chat():
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]
    st.session_state.known = {}
    st.session_state.asked = set()
    st.session_state.stage = "start"
    st.session_state.current_q = None
    st.session_state.duration = None
    st.session_state.complaint = ""


if "messages" not in st.session_state:
    reset_chat()


def say(text, **extra):
    st.session_state.messages.append({"role": "assistant", "content": text, **extra})


# ---------------------------------------------------------------------------
# الشريط الجانبي: ملف المريض
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 👤 ملف المريض")
    st.caption("البيانات دي بتخلي النصيحة الدوائية مناسبة ليك وآمنة.")
    age = st.number_input("السن (بالسنين - للرضيع اكتب كسر مثلاً 0.5 = 6 شهور)", 0.0, 110.0, 25.0, 0.5)
    sex = st.radio("النوع", ["female", "male"], horizontal=True,
                   format_func=lambda x: {"male": "ذكر", "female": "أنثى"}[x])
    weight = st.number_input("الوزن (كجم)", 2.0, 200.0, 70.0, 0.5)
    conds_options = [c for c in PATIENT_CONDITIONS if not (sex == "male" and c in ("pregnancy", "breastfeeding"))]
    conditions = st.multiselect("أمراض مزمنة / حالات خاصة", conds_options, placeholder="اختار لو موجود...",
                                format_func=lambda c: PATIENT_CONDITIONS[c])
    chronic = st.multiselect("أدوية بتاخدها بانتظام", list(CHRONIC_MEDS), placeholder="اختار لو موجود...",
                             format_func=lambda m: CHRONIC_MEDS[m]["name"])
    profile = {"age": age, "sex": sex, "weight": weight, "conditions": conditions}
    st.session_state.profile = profile
    st.session_state.chronic = chronic

    st.divider()
    st.markdown("## 🤖 عقل الوكيل الذكي")
    provider = st.radio("المزوّد", ["gemini", "claude"], horizontal=True,
                        format_func=lambda x: {"gemini": "Google Gemini (مجاني)", "claude": "Anthropic Claude"}[x])

    def _secret(name):
        try:
            return st.secrets.get(name, "")
        except Exception:  # مفيش ملف secrets
            return ""

    client, agent_client, agent_model = None, None, None
    if provider == "gemini":
        key = st.text_input("Google AI Studio API Key", type="password",
                            help="مجاني من aistudio.google.com ← Get API key") or _secret("GEMINI_API_KEY")
        agent_client = gemini_agent.get_client(key)
        if agent_client:
            if st.session_state.get("gemini_models_key") != key:
                st.session_state.gemini_models = gemini_agent.available_models(agent_client)
                st.session_state.gemini_models_key = key
            agent_model = st.selectbox(
                "الموديل", [gemini_agent.AUTO] + st.session_state.gemini_models,
                format_func=lambda m: "⚡ تلقائي (أسرع موديل متاح دلوقتي)" if m == gemini_agent.AUTO else m,
                help="التلقائي بيجرب كذا موديل في أول المحادثة ويختار الأحدث اللي بيرد بسرعة "
                     "(الموديلات الجديدة ساعات بيبقى عليها ضغط).")
    else:
        key = st.text_input("Anthropic API Key", type="password",
                            help="من console.anthropic.com (مدفوع)") or _secret("ANTHROPIC_API_KEY")
        client = agent_client = ai_assistant.get_client(key)
        agent_model = agent.MODEL
    st.session_state.client = client                    # فهم الكلام الحر في المحرك المحلي (Claude بس)
    st.session_state.agent_client = agent_client
    st.session_state.agent_provider = provider
    st.session_state.agent_model = agent_model
    if agent_client:
        st.success(f"الوكيل الذكي الأونلاين شغال ✅ ({agent_model})")
    else:
        st.info("المحرك المحلي الأوفلاين شغال ✅ — حط المفتاح عشان تشغّل الوكيل الأونلاين.")

    st.divider()
    st.markdown("## 🚑 أرقام الطوارئ")
    for k, v in EMERGENCY_NUMBERS.items():
        st.markdown(f"**{k}:** `{v}`")


# ---------------------------------------------------------------------------
# منطق المحادثة (State Machine)
# ---------------------------------------------------------------------------
def handle_text(text: str):
    text = text.strip()
    if not text:
        return
    if st.session_state.stage in ("done", "emergency"):
        reset_chat()
    st.session_state.messages.append({"role": "user", "content": text})
    profile, client = st.session_state.profile, st.session_state.client

    # 1) علامات الخطر أولاً - دايماً
    flags = nlp.detect_red_flags(text)
    if flags:
        st.session_state.stage = "emergency"
        say("", kind="emergency", flags=[f["id"] for f in flags])
        return

    # 2) لو مستنيين إجابة سؤال نعم/لا
    if st.session_state.stage == "questions" and st.session_state.current_q:
        ans = nlp.parse_yes_no(text)
        if ans is not None:
            answer_question(ans, echo=False)
            return

    # 3) استخراج الأعراض من الكلام
    found = nlp.extract_symptoms(text)
    if client:
        for sid, val in ai_assistant.ai_extract_symptoms(client, text).items():
            found.setdefault(sid, val)
    if st.session_state.duration is None:
        st.session_state.duration = nlp.extract_duration_days(text)
    st.session_state.complaint += " " + text

    new = {k: v for k, v in found.items() if k not in st.session_state.known}
    st.session_state.known.update(new)
    if st.session_state.current_q in found:
        st.session_state.asked.add(st.session_state.current_q)

    if not st.session_state.known:
        say("معلش مقدرتش أفهم الأعراض كويس 🙏 ممكن توصفها بطريقة تانية؟ أو اختار من الأعراض الشائعة تحت.",
            kind="chips")
        return

    if new and st.session_state.stage == "start":
        names = "، ".join(("✅ " if v else "❌ ") + SYMPTOMS[k]["name"] for k, v in new.items())
        say(f"تمام، فهمت منك: {names}")
    advance()


def answer_question(ans, echo=True):
    q = st.session_state.current_q
    if echo:
        st.session_state.messages.append({"role": "user", "content": {True: "أيوه", False: "لأ", None: "مش متأكد"}[ans]})
    st.session_state.known[q] = ans
    st.session_state.asked.add(q)
    st.session_state.current_q = None
    if ans and q == "high_fever":
        st.session_state.known["fever"] = True
    advance()


def answer_duration(days):
    labels = {1: "يوم أو يومين", 5: "من 3 لـ 7 أيام", 14: "من أسبوع لـ 3 أسابيع", 30: "أكتر من 3 أسابيع"}
    st.session_state.messages.append({"role": "user", "content": labels[days]})
    st.session_state.duration = days
    advance()


def advance():
    priors = diagnosis.adjusted_priors(st.session_state.profile)
    known, asked = st.session_state.known, st.session_state.asked

    if st.session_state.duration is None and st.session_state.stage != "duration":
        st.session_state.stage = "duration"
        say("⏱️ الأعراض دي بقالها قد إيه؟", kind="duration")
        return

    if not diagnosis.should_stop(known, asked, priors):
        q, gain = diagnosis.next_question(known, asked, priors)
        if q:
            st.session_state.stage = "questions"
            st.session_state.current_q = q
            say(f"**{SYMPTOMS[q]['question']}**", kind="question",
                note=f"🧠 اخترت السؤال ده لأنه أكتر سؤال هيوضّح الصورة (كسب معلومات = {gain:.2f} bit)")
            return
    finish(priors)


def finish(priors):
    known = st.session_state.known
    profile, chronic, client = st.session_state.profile, st.session_state.chronic, st.session_state.client
    post = diagnosis.posterior(known, priors)
    ranking = list(post.items())
    top_id, top_p = ranking[0]
    duration = st.session_state.duration

    allowed, excluded = safety.filter_drugs(top_id, profile, known)
    drug_ids = [d for d, _ in allowed]
    inter = safety.interactions_with_chronic(drug_ids, chronic)
    inter += safety.check_interactions({d: DRUGS[d]["group"] for d in drug_ids}, {d: DRUGS[d]["group"] for d in drug_ids})
    for i in inter:
        i["a_name"], i["b_name"] = safety.any_drug_name(i["a"]), safety.any_drug_name(i["b"])

    child = profile["age"] < 12
    plan = {
        "duration": duration,
        "drugs": [{
            "id": d, "generic": DRUGS[d]["generic"], "brands": DRUGS[d]["brands"], "use": DRUGS[d]["use"],
            "dose": DRUGS[d]["child_dose"] if child else DRUGS[d]["adult_dose"], "notes": DRUGS[d]["notes"],
            "warnings": w,
        } for d, w in allowed],
        "excluded": [(DRUGS[d]["generic"], r) for d, r in excluded],
        "interactions": inter,
        "advice": CONDITIONS[top_id]["advice"] if top_id in CONDITIONS else ["اكشف عند دكتور ممارس عام لتقييم الأعراض."],
        "referral": safety.referral_reasons(top_id, profile, known, duration, top_p),
        "refer_if": CONDITIONS[top_id]["refer_if"] if top_id in CONDITIONS else [],
    }
    result = {
        "top": top_id, "top_p": top_p, "source": CONDITIONS.get(top_id, {}).get("source", ""),
        "ranking": [(diagnosis.condition_name(c), p) for c, p in ranking[:5]],
        "reasons": diagnosis.explain(top_id, known),
        "plan": plan,
    }
    if client:
        summary = (
            f"الحالة الأرجح: {diagnosis.condition_name(top_id)} بنسبة {top_p:.0%}. "
            f"الأعراض: {', '.join(SYMPTOMS[s]['name'] for s, v in known.items() if v)}. "
            f"الأدوية المقترحة: {', '.join(d['generic'] for d in plan['drugs']) or 'لا يوجد'}. "
            f"نصائح: {' '.join(plan['advice'])} "
            f"أسباب التحويل للطبيب: {' '.join(plan['referral']) or 'لا يوجد'}"
        )
        result["ai_text"] = ai_assistant.ai_explain(client, summary)
    result["report"] = build_report(profile, known, result["ranking"], plan, [CHRONIC_MEDS[m]["name"] for m in chronic])
    st.session_state.stage = "done"
    say("", kind="result", result=result)


def add_symptom(sid):
    st.session_state.messages.append({"role": "user", "content": SYMPTOMS[sid]["name"]})
    st.session_state.known[sid] = True
    advance()


# ---------------------------------------------------------------------------
# عرض النتيجة
# ---------------------------------------------------------------------------
def render_emergency(flag_ids):
    flags = [f for f in RED_FLAGS if f["id"] in flag_ids]
    st.markdown("### 🚨 تنبيه طوارئ")
    for f in flags:
        st.markdown(f"<div class='card red'><b>{f['title']}</b><br>{f['action']}</div>", unsafe_allow_html=True)
    st.error("النظام وقف التقييم لأن الأعراض دي محتاجة رعاية طبية فورية ومينفعش تتعالج في الصيدلية. 🚑 الإسعاف: 123")


def render_result(r, idx):
    plan = r["plan"]
    top_name = diagnosis.condition_name(r["top"])
    label = diagnosis.confidence_label(r["top_p"])
    color = "green" if r["top_p"] >= 0.8 else ("amber" if r["top_p"] >= 0.55 else "red")
    st.markdown(
        f"<div class='card {color}'><span class='small'>التقييم المبدئي الأرجح</span>"
        f"<h3 style='margin:0'>🩺 {top_name}</h3>"
        f"<span class='pill'>{r['top_p']:.0%}</span><span class='pill {'' if color == 'green' else color}'>{label}</span></div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📊 التشخيص التفريقي (Differential Diagnosis)**")
        for name, p in r["ranking"][:4]:
            st.progress(min(max(p, 0.0), 1.0), text=f"{name} — {p:.0%}")
    with c2:
        st.markdown("**🔍 ليه وصلت للنتيجة دي؟ (Explainable AI)**")
        for sid, present, lr in r["reasons"]:
            arrow = "⬆️ بيزوّد" if lr > 1 else "⬇️ بيقلل"
            mark = "✅" if present else "❌ مفيش"
            st.markdown(f"- {mark} {SYMPTOMS[sid]['name']} → {arrow} الاحتمال ×{lr if lr > 1 else 1 / lr:.1f}")

    if plan["referral"]:
        st.markdown("<div class='card red'><b>👨‍⚕️ لازم تكشف عند دكتور:</b><ul>"
                    + "".join(f"<li>{x}</li>" for x in plan["referral"]) + "</ul></div>", unsafe_allow_html=True)

    if plan["drugs"]:
        st.markdown("#### 💊 العلاج المقترح بدون روشتة (OTC)")
        for d in plan["drugs"]:
            warn = "".join(f"<br>⚠️ <span class='small'>{w}</span>" for w in d["warnings"])
            st.markdown(
                f"<div class='card'><b>{d['generic']}</b> <span class='pill'>{d['brands']}</span><br>"
                f"<span class='small'>{d['use']}</span><br>📏 <b>الجرعة:</b> {d['dose']}<br>"
                f"💡 {d['notes']}{warn}</div>",
                unsafe_allow_html=True,
            )
    if plan["excluded"]:
        with st.expander(f"🚫 {len(plan['excluded'])} أدوية استبعدناها عشان سلامتك"):
            for name, reasons in plan["excluded"]:
                st.markdown(f"- **{name}**: {'، '.join(reasons)}")
    if plan["interactions"]:
        st.markdown("#### ⚡ تنبيهات التداخلات الدوائية")
        for i in plan["interactions"]:
            cls = "red" if i["severity"] == "major" else "amber"
            st.markdown(f"<div class='card {cls}'><b>[{i['severity_ar']}]</b> {i['a_name']} + {i['b_name']}<br>"
                        f"{i['effect']}<br>✅ {i['advice']}</div>", unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 🌿 نصائح غير دوائية")
        for a in plan["advice"]:
            st.markdown(f"- {a}")
    with c4:
        st.markdown("#### ⏰ ارجع للدكتور لو")
        for a in plan["refer_if"]:
            st.markdown(f"- {a}")

    if r.get("ai_text"):
        st.markdown("#### 🤖 كلمة من شفاء")
        st.info(r["ai_text"])

    if r.get("source"):
        st.caption(f"📚 مصدر معلومات الحالة: {r['source']}")
    st.download_button("📄 نزّل التقرير (HTML - يتطبع PDF)", r["report"], file_name="shefa_report.html",
                       mime="text/html", key=f"dl_{idx}")
    st.caption("⚠️ ده تقييم مبدئي تعليمي ولا يغني عن الطبيب أو الصيدلي.")


# ---------------------------------------------------------------------------
# الوكيل الذكي الأونلاين
# ---------------------------------------------------------------------------
AGENT_GREETING = (
    "أهلاً بيك! أنا **شفاء** 🤖 — الوكيل الذكي.\n\n"
    "احكيلي بتحس بإيه بالعامية زي ما انت بتتكلم. هسألك كام سؤال، وهدوّر بنفسي في **PubMed** و**MedlinePlus** "
    "ونشرات **FDA**، وكل دواء هقترحه هيعدي الأول على فحص الأمان المحلي (أمراضك وأدويتك والتداخلات)."
)


def reset_agent():
    st.session_state.agent_history = []          # الرسايل بصيغة الـ API بتاع المزوّد
    st.session_state.agent_display = [{"role": "assistant", "content": AGENT_GREETING}]
    st.session_state.agent_history_owner = (st.session_state.get("agent_provider"), st.session_state.get("agent_model"))
    st.session_state.gemini_active_model = None  # الموديل اللي اتختار تلقائياً للمحادثة دي


# لو المزوّد أو الموديل اتغير نبدأ محادثة جديدة (صيغة الرسايل بتختلف من مزوّد للتاني)
if ("agent_history" not in st.session_state
        or st.session_state.agent_history_owner != (st.session_state.agent_provider, st.session_state.agent_model)):
    reset_agent()


def agent_send(text: str):
    text = text.strip()
    if not text:
        return
    st.session_state.agent_display.append({"role": "user", "content": text})
    # حاجز أمان بالكود: علامات الخطر بتتفحص قبل ما الرسالة توصل لـ Claude
    flags = nlp.detect_red_flags(text)
    if flags:
        st.session_state.agent_display.append({"role": "assistant", "kind": "emergency", "flags": [f["id"] for f in flags]})
        return
    with st.status("🧠 شفاء بيفكر ويدوّر...", expanded=True) as status:
        def on_tool(ev):
            status.write(f"{ev['label']}: `{ev['input'].get('query') or ev['input'].get('generic_name') or ''}`")
        try:
            args = (st.session_state.agent_client, st.session_state.agent_history, text,
                    st.session_state.profile, st.session_state.chronic)
            if st.session_state.agent_provider == "gemini":
                model = st.session_state.agent_model
                if model == gemini_agent.AUTO:
                    if not st.session_state.gemini_active_model:
                        status.write("⚡ بختار أسرع موديل Gemini متاح دلوقتي...")
                        st.session_state.gemini_active_model = gemini_agent.pick_fast_model(
                            st.session_state.agent_client, st.session_state.gemini_models)
                        status.write(f"✅ الموديل: `{st.session_state.gemini_active_model}`")
                    model = st.session_state.gemini_active_model
                out = gemini_agent.run_turn(
                    *args, on_tool=on_tool, model=model,
                    on_wait=lambda sec: status.write(f"⏳ الخطة المجانية ليها حد في الدقيقة، بستنى {sec:.0f} ثانية وأكمل..."))
            else:
                out = agent.run_turn(*args, on_tool=on_tool)
        except Exception as e:
            msg = f"{type(e).__name__} {e}"
            if any(k in msg for k in ("API key not valid", "API_KEY_INVALID", "AuthenticationError", "invalid x-api-key")):
                text_err = "🔑 المفتاح غلط. انسخه تاني بالظبط من الموقع وحطه في الشريط الجانبي."
            else:
                text_err = (f"⚠️ حصلت مشكلة في الاتصال بالوكيل ({type(e).__name__}: {str(e)[:150]}). "
                            "اتأكد من المفتاح والنت، أو استخدم تبويب المحرك المحلي الأوفلاين.")
            out = {"text": text_err, "events": []}
        status.update(label="✅ خلصت", state="complete", expanded=False)
    st.session_state.agent_display.append({"role": "assistant", "content": out["text"], "events": out["events"]})


# ---------------------------------------------------------------------------
# الواجهة
# ---------------------------------------------------------------------------
st.markdown(
    "<div class='hero'><h1>🩺 شفاء AI</h1>"
    "<p>المساعد الصيدلي الذكي للتقييم المبدئي للأعراض واختيار العلاج الآمن — مشروع تخرج كلية الصيدلة، جامعة القاهرة</p></div>",
    unsafe_allow_html=True,
)

tab_agent, tab_chat, tab_inter, tab_peds, tab_how = st.tabs(
    ["🤖 الوكيل الذكي (أونلاين)", "💬 المحرك المحلي (أوفلاين)", "⚡ فاحص التداخلات", "👶 جرعات الأطفال",
     "🧠 إزاي النظام بيفكر"]
)

with tab_agent:
    if not st.session_state.agent_client:
        st.markdown(
            "<div class='card amber'><b>🔑 الوكيل الذكي محتاج مفتاح API</b><br>"
            "الوكيل بيستخدم Gemini أو Claude كعقل، وبيدور بنفسه في PubMed و MedlinePlus ونشرات FDA.<br>"
            "أسهل حاجة: مفتاح <b>مجاني</b> من <b>aistudio.google.com</b> ← Get API key، وحطه في الشريط الجانبي.<br>"
            "لحد ما تحطه، تبويب <b>المحرك المحلي (أوفلاين)</b> شغال كامل من غير نت.</div>",
            unsafe_allow_html=True,
        )
    else:
        for m in st.session_state.agent_display:
            with st.chat_message(m["role"], avatar="🤖" if m["role"] == "assistant" else "🙂"):
                if m.get("kind") == "emergency":
                    render_emergency(m["flags"])
                    continue
                if m.get("events"):
                    with st.expander(f"🔎 اللي عمله الوكيل ({len(m['events'])} خطوة)"):
                        for ev in m["events"]:
                            arg = ev["input"].get("query") or ev["input"].get("generic_name") or ", ".join(ev["input"].get("drugs", []))
                            st.markdown(f"**{ev['label']}** {f'`{arg}`' if arg else ''}")
                            if ev["summary"]:
                                st.markdown(ev["summary"])
                st.markdown(m["content"])
        if len(st.session_state.agent_display) == 1:
            st.markdown("**جرّب:**")
            agent_examples = {
                "🦵 وجع رجلي من الوقفة": "انا رجلي بتوجعني جامد من الوقفة في الشغل",
                "🤧 رشح وعطس": "عندي رشح وعطس وزوري بيوجعني من يومين",
                "🤢 إسهال": "عندي اسهال ومغص من امبارح بعد ما اكلت من بره",
                "😴 مش عارف انام": "بقالي أسبوعين مش عارف انام كويس",
            }
            cols = st.columns(len(agent_examples))
            for col, (label, txt) in zip(cols, agent_examples.items()):
                if col.button(label, key=f"ag_{label}", width="stretch"):
                    agent_send(txt)
                    st.rerun()
        else:
            st.button("🔄 محادثة جديدة", on_click=reset_agent, key="agent_reset")
        agent_text = st.chat_input("اكتب الأعراض بالعامية...", key="agent_input")
        if agent_text:
            agent_send(agent_text)
            st.rerun()
        st.caption("⚠️ تقييم مبدئي تعليمي ولا يغني عن الطبيب أو الصيدلي.")

with tab_chat:
    col_chat, col_live = st.columns([2.2, 1])
    with col_chat:
        for i, m in enumerate(st.session_state.messages):
            with st.chat_message(m["role"], avatar="🩺" if m["role"] == "assistant" else "🙂"):
                kind = m.get("kind")
                if kind == "emergency":
                    render_emergency(m["flags"])
                elif kind == "result":
                    render_result(m["result"], i)
                else:
                    st.markdown(m["content"])
                    if m.get("note"):
                        st.caption(m["note"])

        stage = st.session_state.stage
        last_kind = st.session_state.messages[-1].get("kind")
        if stage == "start" and len(st.session_state.messages) == 1:
            st.markdown("**جرّب مثال سريع:**")
            examples = {
                "🤧 رشح وعطس": "عندي رشح وعطس كتير ومناخيري مسدودة وعيني بتاكلني من يومين",
                "🤒 سخونية وتكسير": "عندي سخونية 39 وجسمي مكسر وكحة ناشفة من امبارح",
                "🤢 إسهال ومغص": "عندي اسهال ومغص بعد ما اكلت من بره من يوم",
                "🔥 حموضة": "عندي حموضة وحرقان في صدري بعد الاكل بقالها اسبوع",
                "🤕 صداع": "عندي صداع نصفي بيدق والنور بيضايقني",
                "🦵 وجع رجل": "انا رجلي بتوجعني جامد من الوقفة في الشغل",
            }
            cols = st.columns(len(examples))
            for col, (label, txt) in zip(cols, examples.items()):
                col.button(label, on_click=handle_text, args=(txt,), width="stretch")
        elif stage == "questions" and last_kind == "question":
            b1, b2, b3 = st.columns(3)
            b1.button("✅ أيوه", on_click=answer_question, args=(True,), width="stretch")
            b2.button("❌ لأ", on_click=answer_question, args=(False,), width="stretch")
            b3.button("🤷 مش متأكد", on_click=answer_question, args=(None,), width="stretch")
        elif stage == "duration" and last_kind == "duration":
            cols = st.columns(4)
            for col, (days, label) in zip(cols, [(1, "يوم أو يومين"), (5, "3 - 7 أيام"), (14, "1 - 3 أسابيع"), (30, "أكتر من 3 أسابيع")]):
                col.button(label, on_click=answer_duration, args=(days,), width="stretch")
        elif last_kind == "chips":
            common = ["fever", "headache", "cough", "sore_throat", "runny_nose", "diarrhea", "abdominal_cramps",
                      "heartburn", "constipation", "dysuria", "itchy_rash", "red_eye", "leg_pain", "back_pain",
                      "joint_pain", "toothache", "mouth_ulcer", "cant_sleep", "spots_face", "ear_blocked"]
            cols = st.columns(4)
            for n, sid in enumerate(common):
                cols[n % 4].button(SYMPTOMS[sid]["name"], key=f"chip_{sid}", on_click=add_symptom, args=(sid,),
                                   width="stretch")
        if stage in ("done", "emergency"):
            st.button("🔄 استشارة جديدة", on_click=reset_chat, type="primary")

        user_text = st.chat_input("اكتب الأعراض أو ردك هنا...", key="local_input")
        if user_text:
            handle_text(user_text)
            st.rerun()

    with col_live:
        st.markdown("#### 📈 التفكير المباشر")
        st.caption("الاحتمالات بتتحدث مع كل إجابة (Bayesian Updating)")
        if not st.session_state.known:
            st.info("احكي الأعراض وهتشوف الاحتمالات بتتغير هنا لحظة بلحظة.")
        else:
            priors = diagnosis.adjusted_priors(profile)
            live = diagnosis.posterior(st.session_state.known, priors)
            for cid, p in list(live.items())[:5]:
                st.progress(min(max(p, 0.0), 1.0), text=f"{diagnosis.condition_name(cid)} — {p:.0%}")
        if st.session_state.known:
            st.markdown("**الأعراض المعروفة:**")
            for sid, v in st.session_state.known.items():
                mark = {True: "✅", False: "❌", None: "🤷"}[v]
                st.markdown(f"<span class='small'>{mark} {SYMPTOMS[sid]['name']}</span>", unsafe_allow_html=True)
        if st.session_state.duration is not None:
            st.markdown(f"<span class='small'>⏱️ المدة: {st.session_state.duration} يوم</span>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
with tab_inter:
    st.markdown("### ⚡ فاحص التداخلات الدوائية")
    st.caption("اختار أي مجموعة أدوية (بدون روشتة أو مزمنة) والنظام هيفحص كل الأزواج الممكنة.")
    all_opts = {**{d: f"{v['generic']} — {v['brands']}" for d, v in DRUGS.items()},
                **{m: v["name"] for m, v in CHRONIC_MEDS.items()}}
    picked = st.multiselect("الأدوية", list(all_opts), default=chronic, format_func=lambda x: all_opts[x],
                            placeholder="اختار الأدوية...")
    if len(picked) >= 2:
        groups = {p: (DRUGS[p]["group"] if p in DRUGS else CHRONIC_MEDS[p]["group"]) for p in picked}
        res = safety.check_interactions(groups, groups)
        pairs = len(picked) * (len(picked) - 1) // 2
        st.markdown(f"تم فحص **{pairs}** زوج من الأدوية.")
        if not res:
            st.markdown("<div class='card green'>✅ لا توجد تداخلات معروفة في قاعدة البيانات بين الأدوية دي.</div>",
                        unsafe_allow_html=True)
        for i in res:
            cls = {"major": "red", "moderate": "amber", "minor": ""}[i["severity"]]
            st.markdown(f"<div class='card {cls}'><b>[{i['severity_ar']}]</b> {safety.any_drug_name(i['a'])} + "
                        f"{safety.any_drug_name(i['b'])}<br>{i['effect']}<br>✅ <b>الحل:</b> {i['advice']}</div>",
                        unsafe_allow_html=True)
    else:
        st.info("اختار دوائين على الأقل.")

# ---------------------------------------------------------------------------
with tab_peds:
    st.markdown("### 👶 حاسبة جرعات الأطفال بالوزن")
    c1, c2 = st.columns(2)
    with c1:
        drug = st.radio("الدواء", ["paracetamol", "ibuprofen"],
                        format_func=lambda x: {"paracetamol": "Paracetamol (Abimol / Panadol Baby)",
                                               "ibuprofen": "Ibuprofen (Brufen Syrup)"}[x])
        conc_opts = {"paracetamol": [120, 160, 250], "ibuprofen": [100, 200]}[drug]
        conc = st.selectbox("تركيز الشراب (مجم / 5 مل)", conc_opts)
        w = st.number_input("وزن الطفل (كجم)", 2.0, 80.0, 12.0, 0.5)
        a = st.number_input("سن الطفل (بالسنين)", 0.0, 16.0, 2.0, 0.25)
    with c2:
        res = safety.pediatric_dose(drug, w, a, conc)
        if res["ok"]:
            st.markdown(f"<div class='card green'>الجرعة الواحدة<div class='big-dose'>{res['dose_ml']} مل</div>"
                        f"= {res['dose_mg']} مجم — {res['interval']}<br>"
                        f"أقصى عدد جرعات: {res['max_doses']} في اليوم<br>"
                        f"أقصى جرعة يومية: {res['daily_max_mg']} مجم ({res['daily_max_ml']} مل)</div>",
                        unsafe_allow_html=True)
            st.caption("استخدم السرنجة أو الكوباية المدرّجة اللي مع العلبة - مش معلقة البيت.")
        else:
            st.error(res["message"])

# ---------------------------------------------------------------------------
with tab_how:
    st.markdown("### 🧠 إزاي شفاء بيفكر؟")
    st.graphviz_chart(
        """
digraph G {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#e0f2f1", color="#0b7a75", fontname="Arial"];
  A [label="كلام المريض\\n(عامية / فصحى / English)"];
  B [label="1. فحص علامات الخطر\\nRed Flags", fillcolor="#ffcdd2"];
  C [label="2. فهم اللغة NLP\\n+ Claude (اختياري)"];
  D [label="3. محرك Bayes\\nالاحتمالات"];
  E [label="4. اختيار السؤال الأذكى\\nInformation Gain"];
  F [label="5. طبقة الأمان الدوائي\\nموانع + تداخلات + جرعات", fillcolor="#fff8e1"];
  G [label="6. الخطة + التقرير\\n+ قرار التحويل"];
  H [label="🚑 طوارئ 123", fillcolor="#ef9a9a"];
  A -> B; B -> H [label="خطر"]; B -> C [label="آمن"]; C -> D; D -> E; E -> D [label="إجابة"]; D -> F [label="ثقة كافية"]; F -> G;
}
"""
    )
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("أعراض", len(SYMPTOMS))
    m2.metric("حالات مرضية", len(CONDITIONS))
    m3.metric("أدوية OTC", len(DRUGS))
    m4.metric("تداخلات", len(INTERACTIONS))
    m5.metric("علامات خطر", len(RED_FLAGS))
    st.markdown(
        r"""
**نظرية بايز (Bayes' Theorem):**
$$P(\text{Disease}\mid\text{Symptoms}) = \frac{P(\text{Disease})\times\prod_i P(S_i\mid\text{Disease})}{P(\text{Symptoms})}$$

**كسب المعلومات (Information Gain):**
$$IG(S) = H(D) - \left[P(S)\,H(D\mid S{=}\text{yes}) + P(\neg S)\,H(D\mid S{=}\text{no})\right]$$
حيث $H(D) = -\sum P(d)\log_2 P(d)$ هي الإنتروبي (مقياس عدم اليقين).
"""
    )
    if st.session_state.known:
        st.markdown("#### 🔬 الحسابات للجلسة الحالية")
        priors = diagnosis.adjusted_priors(profile)
        post = diagnosis.posterior(st.session_state.known, priors)
        rows = []
        for cid, p in list(post.items())[:6]:
            row = {"الحالة": diagnosis.condition_name(cid), "Prior": f"{priors[cid]:.3f}"}
            for sid, v in st.session_state.known.items():
                if v is not None:
                    lk = diagnosis._likelihood(cid, sid)
                    row[SYMPTOMS[sid]["name"][:18]] = f"{lk if v else 1 - lk:.2f}"
            row["Posterior"] = f"{p:.1%}"
            rows.append(row)
        st.dataframe(rows)
        st.caption(f"الإنتروبي الحالية (عدم اليقين): {diagnosis.entropy(post):.2f} bit")
