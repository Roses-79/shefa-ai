"""
اختبارات المحرك (Unit Tests + Clinical Vignettes).
للتشغيل:  python -m unittest discover tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import diagnosis, nlp, safety  # noqa: E402
from engine.knowledge_base import CONDITIONS, DRUGS, INTERACTIONS, SYMPTOMS  # noqa: E402

ADULT_F = {"age": 25, "sex": "female", "conditions": []}
ADULT_M = {"age": 30, "sex": "male", "conditions": []}


def simulate(text, profile, true_condition):
    """محاكاة مريض افتراضي بيجاوب على الأسئلة حسب الحالة الحقيقية بتاعته."""
    priors = diagnosis.adjusted_priors(profile)
    known = nlp.extract_symptoms(text)
    asked = set()
    while not diagnosis.should_stop(known, asked, priors):
        q, _ = diagnosis.next_question(known, asked, priors)
        if q is None:
            break
        known[q] = CONDITIONS[true_condition]["likelihoods"].get(q, 0) >= 0.5
        asked.add(q)
    post = diagnosis.posterior(known, priors)
    return next(iter(post)), len(asked)


class TestNLP(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(nlp.normalize("إسهالٌ وحرارة"), "اسهال وحراره")

    def test_egyptian_dialect(self):
        found = nlp.extract_symptoms("عندي سخونية وكحة ناشفة وجسمي مكسر")
        self.assertTrue(found["fever"])
        self.assertTrue(found["cough_dry"])
        self.assertTrue(found["cough"])
        self.assertTrue(found["body_aches"])

    def test_negation(self):
        found = nlp.extract_symptoms("عندي رشح ومفيش سخونية")
        self.assertTrue(found["runny_nose"])
        self.assertFalse(found["fever"])

    def test_english(self):
        found = nlp.extract_symptoms("I have a sore throat and no fever")
        self.assertTrue(found["sore_throat"])
        self.assertFalse(found["fever"])

    def test_temperature(self):
        found = nlp.extract_symptoms("حرارتي 39.5")
        self.assertTrue(found["high_fever"])
        found = nlp.extract_symptoms("الحرارة 37 درجة")
        self.assertFalse(found["fever"])

    def test_duration(self):
        self.assertEqual(nlp.extract_duration_days("من 3 ايام"), 3)
        self.assertEqual(nlp.extract_duration_days("بقالي اسبوعين"), 14)
        self.assertEqual(nlp.extract_duration_days("since 2 weeks"), 14)

    def test_red_flags(self):
        ids = [f["id"] for f in nlp.detect_red_flags("عندي ألم في صدري وضيق تنفس")]
        self.assertIn("chest_pain", ids)
        self.assertIn("breathing", ids)
        self.assertEqual(nlp.detect_red_flags("عندي رشح بسيط"), [])

    def test_no_false_match(self):
        # "حمية" (رجيم) مش لازم تتفهم "حمى"
        self.assertNotIn("fever", nlp.extract_symptoms("انا عامله حميه"))

    def test_yes_no(self):
        self.assertTrue(nlp.parse_yes_no("ايوه"))
        self.assertFalse(nlp.parse_yes_no("لأ"))
        self.assertIsNone(nlp.parse_yes_no("ممكن"))


class TestDiagnosis(unittest.TestCase):
    def test_probabilities_sum_to_one(self):
        post = diagnosis.posterior({"fever": True}, diagnosis.adjusted_priors(ADULT_F))
        self.assertAlmostEqual(sum(post.values()), 1.0, places=6)

    def test_male_no_dysmenorrhea(self):
        self.assertEqual(diagnosis.adjusted_priors(ADULT_M)["dysmenorrhea"], 0)

    def test_info_gain_positive(self):
        priors = diagnosis.adjusted_priors(ADULT_F)
        q, gain = diagnosis.next_question({"headache": True}, set(), priors)
        self.assertIsNotNone(q)
        self.assertGreater(gain, 0)

    def test_clinical_vignettes(self):
        cases = [
            ("عندي رشح وعطس ومناخيري مسدودة", "common_cold"),
            ("عندي سخونية عالية فجأة وجسمي مكسر ورعشة", "influenza"),
            ("عطس كتير وعيني بتاكلني مع التراب", "allergic_rhinitis"),
            ("زوري بيوجعني جامد وانا ببلع", "pharyngitis"),
            ("عندي كحة ببلغم", "acute_bronchitis"),
            ("اسهال ومغص", "gastroenteritis"),
            ("عندي امساك وبطني منفوخه", "constipation"),
            ("حموضة وطعم مر في بقي", "gerd"),
            ("صداع ضاغط زي الرباط ومضغوط في الشغل", "tension_headache"),
            ("صداع نصفي بيدق", "migraine"),
            ("حرقان في البول", "uti"),
            ("مغص الدوره", "dysmenorrhea"),
            ("هرش وبقعة دائرية حمرا", "tinea"),
            ("عيني حمرا وفيها عماص", "bacterial_conjunctivitis"),
        ]
        correct = 0
        for text, truth in cases:
            predicted, n_q = simulate(text, ADULT_F, truth)
            self.assertLessEqual(n_q, diagnosis.MAX_QUESTIONS)
            correct += predicted == truth
        accuracy = correct / len(cases)
        print(f"\nVignette accuracy: {correct}/{len(cases)} = {accuracy:.0%}")
        self.assertGreaterEqual(accuracy, 0.85)


class TestSafety(unittest.TestCase):
    def test_ulcer_excludes_nsaid(self):
        allowed, excluded = safety.filter_drugs("tension_headache", {"age": 40, "conditions": ["peptic_ulcer"]}, {})
        self.assertIn("ibuprofen", [d for d, _ in excluded])
        self.assertIn("paracetamol", [d for d, _ in allowed])

    def test_hypertension_excludes_decongestant(self):
        _, excluded = safety.filter_drugs("common_cold", {"age": 50, "conditions": ["hypertension"]}, {})
        self.assertIn("pseudoephedrine_combo", [d for d, _ in excluded])

    def test_child_age_limits(self):
        _, excluded = safety.filter_drugs("gastroenteritis", {"age": 5, "conditions": []}, {})
        self.assertIn("loperamide", [d for d, _ in excluded])

    def test_loperamide_with_fever(self):
        _, excluded = safety.filter_drugs("gastroenteritis", {"age": 30, "conditions": []}, {"fever": True})
        self.assertIn("loperamide", [d for d, _ in excluded])

    def test_warfarin_ibuprofen_major(self):
        res = safety.interactions_with_chronic(["ibuprofen"], ["warfarin"])
        self.assertEqual(res[0]["severity"], "major")

    def test_paracetamol_duplication(self):
        groups = {"paracetamol": "paracetamol", "pseudoephedrine_combo": "decongestant_oral"}
        self.assertTrue(safety.check_interactions(groups, groups))

    def test_peds_paracetamol(self):
        r = safety.pediatric_dose("paracetamol", 10, 1, 120)
        self.assertEqual(r["dose_mg"], 150)
        self.assertEqual(r["dose_ml"], 6.2)

    def test_peds_ibuprofen_too_young(self):
        self.assertFalse(safety.pediatric_dose("ibuprofen", 5, 0.3, 100)["ok"])

    def test_peds_dose_cap(self):
        self.assertEqual(safety.pediatric_dose("paracetamol", 90, 15, 250)["dose_mg"], 1000)

    def test_uti_male_referral(self):
        reasons = safety.referral_reasons("uti", ADULT_M, {}, 1, 0.9)
        self.assertTrue(any("الرجالة" in r for r in reasons))


class TestKnowledgeBaseIntegrity(unittest.TestCase):
    def test_references_valid(self):
        groups = {d["group"] for d in DRUGS.values()}
        for cid, c in CONDITIONS.items():
            for sid in c["likelihoods"]:
                self.assertIn(sid, SYMPTOMS, f"{cid}: {sid}")
                self.assertTrue(0 < c["likelihoods"][sid] < 1)
            for did in c["drugs"]:
                self.assertIn(did, DRUGS, f"{cid}: {did}")
        self.assertTrue(groups)
        self.assertTrue(INTERACTIONS)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# التوسعة: حالات العضلات والجلد والفم والأذن...
# ---------------------------------------------------------------------------
class TestExtendedKnowledge(unittest.TestCase):
    def test_leg_pain_from_standing(self):
        # الجملة اللي كان النظام مش بيفهمها
        found = nlp.extract_symptoms("انا رجلي بتوجعني جامد من الوقفة في الشغل")
        self.assertTrue(found["leg_pain"])
        self.assertTrue(found["prolonged_standing"])
        post = diagnosis.posterior(found, diagnosis.adjusted_priors(ADULT_M))
        self.assertIn(next(iter(post)), {"muscle_strain", "varicose_veins"})

    def test_ear_not_confused_with_nose(self):
        found = nlp.extract_symptoms("ودني مسدوده")
        self.assertEqual(found, {"ear_blocked": True})

    def test_negation_inside_phrase(self):
        found = nlp.extract_symptoms("مناخيري مش مسدوده بس برشح")
        self.assertFalse(found["nasal_congestion"])
        self.assertTrue(found["runny_nose"])

    def test_new_red_flags(self):
        ids = [f["id"] for f in nlp.detect_red_flags("رجلي وارمه وحمرا وسخنه")]
        self.assertIn("dvt", ids)
        ids = [f["id"] for f in nlp.detect_red_flags("ضهري بيوجعني ومش قادر اتحكم في البول")]
        self.assertIn("cauda_equina", ids)

    def test_new_vignettes(self):
        cases = [
            ("انا رجلي بتوجعني جامد من الوقفة في الشغل", "varicose_veins"),
            ("انا رجلي بتوجعني جامد من الوقفة في الشغل", "muscle_strain"),
            ("ضهري بيوجعني من ساعة ما شلت حاجه تقيله", "low_back_pain"),
            ("اتلوت رجلي ووارمه", "ankle_sprain"),
            ("كعب رجلي بيوجعني", "plantar_fasciitis"),
            ("شد في رجلي", "leg_cramps"),
            ("عندي حب الشباب", "acne"),
            ("جلدي ناشف وبياكلني", "eczema"),
            ("ارتكاريا", "urticaria"),
            ("فقاقيع على شفايفي", "cold_sores"),
            ("قعدت في الشمس وجلدي احمر", "sunburn"),
            ("عندي قشره", "dandruff"),
            ("عندي قرحه في بقي", "mouth_ulcers"),
            ("ودني مسدوده", "ear_wax"),
            ("سناني بتوجعني", "toothache"),
            ("هرش ورا بالليل", "threadworms"),
            ("بدوخ في العربيه", "motion_sickness"),
            ("هرش في المنطقه الحساسه", "vaginal_thrush"),
            ("مش عارف انام", "insomnia"),
        ]
        correct = sum(simulate(text, ADULT_F, truth)[0] == truth for text, truth in cases)
        print(f"\nExtended vignette accuracy: {correct}/{len(cases)}")
        self.assertGreaterEqual(correct / len(cases), 0.85)

    def test_age_sex_rules(self):
        self.assertEqual(diagnosis.adjusted_priors({"age": 30, "sex": "female"})["nappy_rash"], 0)
        self.assertEqual(diagnosis.adjusted_priors(ADULT_M)["vaginal_thrush"], 0)

    def test_every_condition_has_source(self):
        for cid, c in CONDITIONS.items():
            self.assertTrue(c.get("source"), cid)


# ---------------------------------------------------------------------------
# المصادر الأونلاين (اختبار قراءة الردود بعينات بنفس شكل الردود الحقيقية - من غير نت)
# ---------------------------------------------------------------------------
PUBMED_XML = b"""<?xml version="1.0"?><PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345</PMID>
<Article><Journal><Title>BMJ</Title><JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue></Journal>
<ArticleTitle>Plantar heel pain: a <i>systematic</i> review.</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">Heel pain is common.</AbstractText><AbstractText>Stretching helps.</AbstractText></Abstract>
<PublicationTypeList><PublicationType>Journal Article</PublicationType><PublicationType>Review</PublicationType></PublicationTypeList>
</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""

MEDLINEPLUS_XML = b"""<?xml version="1.0"?><nlmSearchResult><list num="1"><document rank="0" url="https://medlineplus.gov/varicoseveins.html">
<content name="title">&lt;span class="qt0"&gt;Varicose&lt;/span&gt; Veins</content>
<content name="FullSummary">&lt;p&gt;Varicose veins are swollen, twisted veins.&lt;/p&gt;</content></document></list></nlmSearchResult>"""


class TestOnlineParsers(unittest.TestCase):
    def test_pubmed(self):
        from engine.online_sources import parse_pubmed_xml
        r = parse_pubmed_xml(PUBMED_XML)[0]
        self.assertEqual(r["pmid"], "12345")
        self.assertEqual(r["year"], "2023")
        self.assertIn("systematic", r["title"])
        self.assertIn("Stretching helps", r["abstract"])
        self.assertEqual(r["type"], "Review")
        self.assertEqual(r["url"], "https://pubmed.ncbi.nlm.nih.gov/12345/")

    def test_medlineplus(self):
        from engine.online_sources import parse_medlineplus_xml
        r = parse_medlineplus_xml(MEDLINEPLUS_XML)[0]
        self.assertEqual(r["title"], "Varicose Veins")
        self.assertEqual(r["summary"], "Varicose veins are swollen, twisted veins.")

    def test_openfda(self):
        from engine.online_sources import parse_openfda
        data = {"results": [{"openfda": {"brand_name": ["Advil"]}, "warnings": ["Stomach bleeding warning"],
                             "do_not_use": ["right before or after heart surgery"]}]}
        r = parse_openfda("ibuprofen", data)
        self.assertEqual(r["brand_names"], ["Advil"])
        self.assertIn("Stomach bleeding", r["warnings"])
        self.assertIn("error", parse_openfda("x", {"results": []}))


# ---------------------------------------------------------------------------
# الوكيل الذكي (بعميل Claude وهمي بيمثل سيناريو كامل)
# ---------------------------------------------------------------------------
class _FakeMessages:
    def __init__(self, script):
        self.script, self.calls = script, []

    def create(self, **kwargs):
        from types import SimpleNamespace as NS
        self.calls.append(kwargs)
        step = self.script[len(self.calls) - 1]
        blocks = [NS(type="tool_use", id=f"t{i}", name=n, input=a) for i, (n, a) in enumerate(step.get("tools", []))]
        if "text" in step:
            blocks.append(NS(type="text", text=step["text"]))
        return NS(content=blocks, stop_reason="tool_use" if blocks and blocks[0].type == "tool_use" else "end_turn")


class TestAgent(unittest.TestCase):
    def run_agent(self, script, profile, chronic):
        from types import SimpleNamespace as NS
        from engine import agent
        client = NS(beta=NS(messages=_FakeMessages(script)))
        history = []
        out = agent.run_turn(client, history, "رجلي بتوجعني من الوقفة", profile, chronic)
        return out, history, client.beta.messages.calls

    def test_agent_loop_and_safety_tool(self):
        script = [
            {"tools": [("local_differential", {"patient_text": "رجلي بتوجعني من الوقفة", "duration_days": 3})]},
            {"tools": [("check_drug_safety", {"drugs": ["Brufen", "Voltaren", "Panadol", "amoxicillin"]})]},
            {"text": "التقييم المبدئي: إجهاد عضلي"},
        ]
        out, history, calls = self.run_agent(script, {"age": 40, "sex": "male", "weight": 80,
                                                       "conditions": ["peptic_ulcer"]}, ["warfarin"])
        self.assertEqual(out["text"], "التقييم المبدئي: إجهاد عضلي")
        self.assertEqual([e["tool"] for e in out["events"]], ["local_differential", "check_drug_safety"])
        self.assertIn("🚫", out["events"][1]["summary"])          # Brufen ممنوع مع القرحة
        self.assertIn("❔", out["events"][1]["summary"])          # amoxicillin مش OTC
        self.assertEqual([m["role"] for m in history], ["user", "assistant", "user", "assistant", "user", "assistant"])
        self.assertIn("قرحة", history[0]["content"][0]["text"])   # ملف المريض بيوصل للوكيل
        self.assertEqual(calls[0]["model"], "claude-opus-5-5")

    def test_drug_safety_tool(self):
        from engine.agent import tool_check_drug_safety
        r = tool_check_drug_safety(["ibuprofen", "Daflon"], {"age": 30, "conditions": ["pregnancy"]}, ["warfarin"])
        status = {d["drug"]: d["status"] for d in r["drugs"]}
        self.assertEqual(status["ibuprofen"], "excluded")
        self.assertEqual(status["Daflon"], "allowed")


# ---------------------------------------------------------------------------
# الوكيل بعقل Gemini (بأنواع google-genai الحقيقية وسيرفر وهمي)
# ---------------------------------------------------------------------------
class TestGeminiAgent(unittest.TestCase):
    def setUp(self):
        from engine import gemini_agent
        if gemini_agent.genai is None:
            self.skipTest("google-genai not installed")
        self.ga = gemini_agent

    def test_tool_declarations_valid(self):
        decls = self.ga._declarations()
        self.assertEqual(len(decls), 6)
        self.assertNotIn("additionalProperties", str(decls[0].parameters_json_schema))

    def test_loop(self):
        from types import SimpleNamespace as NS
        from google.genai import types

        def reply(parts):
            return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=parts))])

        def call(name, args):
            return types.Part(function_call=types.FunctionCall(id=f"c_{name}", name=name, args=args))

        script = [
            reply([call("local_differential", {"patient_text": "رجلي بتوجعني من الوقفة", "duration_days": 3})]),
            reply([call("check_drug_safety", {"drugs": ["Brufen", "Panadol"]})]),
            reply([types.Part(text="التقييم المبدئي: إجهاد عضلي")]),
        ]
        calls = []

        def generate_content(**kw):
            calls.append(kw)
            return script[len(calls) - 1]

        client = NS(models=NS(generate_content=generate_content))
        history = []
        out = self.ga.run_turn(client, history, "رجلي بتوجعني من الوقفة",
                               {"age": 40, "sex": "male", "weight": 80, "conditions": ["peptic_ulcer"]}, ["warfarin"])
        self.assertEqual(out["text"], "التقييم المبدئي: إجهاد عضلي")
        self.assertEqual([e["tool"] for e in out["events"]], ["local_differential", "check_drug_safety"])
        self.assertIn("🚫", out["events"][1]["summary"])
        self.assertEqual([c.role for c in history], ["user", "model", "user", "model", "user", "model"])
        fr = history[2].parts[0].function_response
        self.assertEqual((fr.id, fr.name), ("c_local_differential", "local_differential"))
        self.assertTrue(calls[0]["config"].automatic_function_calling.disable)

    def test_model_ranking(self):
        from types import SimpleNamespace as NS
        models = [NS(name=f"models/{n}", supported_actions=["generateContent"]) for n in
                  ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
                   "gemini-2.5-flash-image", "text-embedding-004"]]
        client = NS(models=NS(list=lambda: models))
        names = self.ga.available_models(client)
        self.assertEqual(names[0], "gemini-2.5-flash")
        self.assertNotIn("gemini-2.5-flash-image", names)
        self.assertNotIn("text-embedding-004", names)
