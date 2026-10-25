"""
مصادر المعرفة الأونلاين (Online Knowledge Sources) اللي الوكيل الذكي بيدور فيها بنفسه.

  1. PubMed      : أكبر قاعدة أبحاث طبية في العالم (أكتر من 36 مليون بحث) - من المكتبة الوطنية الأمريكية للطب NLM.
                   بنستخدم NCBI E-utilities: esearch (البحث) + efetch (الملخصات).
  2. MedlinePlus : موسوعة صحية موثوقة للمرضى من نفس المكتبة (NLM / NIH).
  3. openFDA     : النشرات الرسمية للأدوية (Drug labels) من هيئة الغذاء والدواء الأمريكية FDA.

كلهم مجانيين ومش محتاجين تسجيل. لو النت قاطع، الدوال بترجع {"error": ...} والوكيل بيكمل بالمعرفة المحلية.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

TIMEOUT = 15
USER_AGENT = "ShefaAI/1.0 (pharmacy graduation project)"

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
MEDLINEPLUS = "https://wsearch.nlm.nih.gov/ws/query"
OPENFDA_LABEL = "https://api.fda.gov/drug/label.json"


def _get(url: str, params: dict) -> bytes:
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _clean(text: str, limit: int) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " ..."


# ---------------------------------------------------------------------------
# PubMed
# ---------------------------------------------------------------------------
def pubmed_search(query: str, max_results: int = 5) -> dict:
    """يدور في PubMed ويرجع العناوين والملخصات. الأولوية للمراجعات المنهجية والإرشادات الحديثة."""
    max_results = max(1, min(int(max_results), 8))
    try:
        ids = json.loads(_get(PUBMED_SEARCH, {
            "db": "pubmed", "term": query, "retmax": max_results, "retmode": "json", "sort": "relevance",
        }))["esearchresult"]["idlist"]
        if not ids:
            return {"query": query, "results": [], "note": "No PubMed results. Try simpler English keywords."}
        xml = _get(PUBMED_FETCH, {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "rettype": "abstract"})
        return {"query": query, "results": parse_pubmed_xml(xml)}
    except Exception as e:  # النت قاطع أو الخدمة واقفة
        return {"query": query, "error": f"PubMed unavailable: {type(e).__name__}"}


def parse_pubmed_xml(xml: bytes) -> list:
    results = []
    for art in ET.fromstring(xml).iter("PubmedArticle"):
        pmid = art.findtext(".//PMID", "")
        title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
        abstract = " ".join("".join(t.itertext()) for t in art.iter("AbstractText"))
        year = art.findtext(".//PubDate/Year") or art.findtext(".//PubDate/MedlineDate", "")[:4]
        types = [t.text for t in art.iter("PublicationType") if t.text]
        results.append({
            "pmid": pmid,
            "title": _clean(title, 300),
            "journal": art.findtext(".//Journal/Title", ""),
            "year": year,
            "type": ", ".join(t for t in types if t != "Journal Article")[:120],
            "abstract": _clean(abstract, 1200),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return results


# ---------------------------------------------------------------------------
# MedlinePlus
# ---------------------------------------------------------------------------
def medlineplus_search(query: str, max_results: int = 3) -> dict:
    """يدور في موضوعات MedlinePlus الصحية (لغة بسيطة موجهة للمرضى)."""
    max_results = max(1, min(int(max_results), 5))
    try:
        xml = _get(MEDLINEPLUS, {"db": "healthTopics", "term": query, "retmax": max_results})
        return {"query": query, "results": parse_medlineplus_xml(xml)}
    except Exception as e:
        return {"query": query, "error": f"MedlinePlus unavailable: {type(e).__name__}"}


def parse_medlineplus_xml(xml: bytes) -> list:
    results = []
    for doc in ET.fromstring(xml).iter("document"):
        fields = {c.get("name"): "".join(c.itertext()) for c in doc.iter("content")}
        results.append({
            "title": _clean(fields.get("title", ""), 200),
            "url": doc.get("url", ""),
            "summary": _clean(fields.get("FullSummary") or fields.get("snippet", ""), 1500),
        })
    return results


# ---------------------------------------------------------------------------
# openFDA
# ---------------------------------------------------------------------------
LABEL_SECTIONS = [
    "indications_and_usage", "dosage_and_administration", "contraindications", "warnings",
    "do_not_use", "ask_doctor", "stop_use", "pregnancy_or_breast_feeding", "drug_interactions",
]


def openfda_label(generic_name: str) -> dict:
    """يجيب أهم أجزاء النشرة الرسمية للدواء من FDA (دواعي الاستعمال، الموانع، التحذيرات، التداخلات)."""
    name = re.sub(r"[^a-zA-Z0-9 \-]", "", generic_name).strip()
    if not name:
        return {"error": "Use the English generic name, e.g. ibuprofen"}
    try:
        data = json.loads(_get(OPENFDA_LABEL, {"search": f'openfda.generic_name:"{name}"', "limit": 1}))
        return parse_openfda(name, data)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"drug": name, "error": "Not found in openFDA (try the generic English name)"}
        return {"drug": name, "error": f"openFDA unavailable: HTTP {e.code}"}
    except Exception as e:
        return {"drug": name, "error": f"openFDA unavailable: {type(e).__name__}"}


def parse_openfda(name: str, data: dict) -> dict:
    results = data.get("results") or []
    if not results:
        return {"drug": name, "error": "Not found in openFDA"}
    label = results[0]
    out = {
        "drug": name,
        "brand_names": label.get("openfda", {}).get("brand_name", [])[:5],
        "source": "openFDA drug label (U.S. FDA)",
        "url": f"https://open.fda.gov/apis/drug/label/ (search: {name})",
    }
    for section in LABEL_SECTIONS:
        if label.get(section):
            out[section] = _clean(" ".join(label[section]), 700)
    return out
