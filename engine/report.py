"""توليد تقرير HTML للمريض يقدر يطبعه أو يوريه للدكتور."""
import html
from datetime import datetime

from .knowledge_base import PATIENT_CONDITIONS, SYMPTOMS


def build_report(profile: dict, known: dict, ranking: list, plan: dict, chronic_names: list) -> str:
    e = html.escape
    present = [SYMPTOMS[s]["name"] for s, v in known.items() if v]
    absent = [SYMPTOMS[s]["name"] for s, v in known.items() if v is False]
    conds = [PATIENT_CONDITIONS[c] for c in profile.get("conditions", [])]
    sex = {"male": "ذكر", "female": "أنثى"}.get(profile.get("sex"), "-")

    rows = "".join(
        f"<tr><td>{e(name)}</td><td>{p * 100:.0f}%</td></tr>" for name, p in ranking[:3]
    )
    drugs = "".join(
        f"<li><b>{e(d['generic'])}</b> ({e(d['brands'])}) — {e(d['dose'])}"
        + "".join(f"<br><small>⚠️ {e(w)}</small>" for w in d["warnings"]) + "</li>"
        for d in plan["drugs"]
    ) or "<li>لا يوجد</li>"
    excluded = "".join(f"<li>{e(name)}: {e('، '.join(r))}</li>" for name, r in plan["excluded"]) or "<li>لا يوجد</li>"
    inter = "".join(
        f"<li>[{e(i['severity_ar'])}] {e(i['a_name'])} + {e(i['b_name'])}: {e(i['effect'])}</li>" for i in plan["interactions"]
    ) or "<li>لا توجد تداخلات معروفة</li>"
    advice = "".join(f"<li>{e(a)}</li>" for a in plan["advice"])
    refer = "".join(f"<li>{e(r)}</li>" for r in plan["referral"]) or "<li>لا يوجد سبب للتحويل حالياً - تابع الأعراض</li>"

    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير شفاء AI</title>
<style>
body{{font-family:Tahoma,Arial,sans-serif;max-width:800px;margin:24px auto;padding:0 16px;color:#1b2b34;line-height:1.7}}
h1{{color:#0b7a75;margin-bottom:0}} h2{{color:#0b7a75;border-bottom:2px solid #e0f2f1;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #cfd8dc;padding:6px 10px}}
.box{{background:#fff8e1;border-right:5px solid #ffb300;padding:10px 14px;border-radius:6px}}
.muted{{color:#607d8b;font-size:13px}}
</style></head><body>
<h1>🩺 شفاء AI — تقرير تقييم مبدئي</h1>
<p class="muted">تاريخ التقرير: {datetime.now():%Y-%m-%d %H:%M}</p>
<h2>بيانات المريض</h2>
<p>السن: {e(str(profile.get('age', '-')))} سنة — النوع: {sex} — الوزن: {e(str(profile.get('weight', '-')))} كجم<br>
الأمراض المزمنة/حالات خاصة: {e('، '.join(conds) or 'لا يوجد')}<br>
الأدوية الحالية: {e('، '.join(chronic_names) or 'لا يوجد')}</p>
<h2>الأعراض</h2>
<p><b>موجودة:</b> {e('، '.join(present) or '-')}<br><b>غير موجودة:</b> {e('، '.join(absent) or '-')}<br>
<b>المدة:</b> {e(str(plan.get('duration') or 'غير محددة'))} يوم</p>
<h2>التشخيص التفريقي المبدئي</h2>
<table><tr><th>الحالة</th><th>الاحتمال</th></tr>{rows}</table>
<h2>الخطة العلاجية المقترحة (OTC)</h2><ul>{drugs}</ul>
<h3>أدوية تم استبعادها لأسباب أمان</h3><ul>{excluded}</ul>
<h3>التداخلات الدوائية</h3><ul>{inter}</ul>
<h2>نصائح</h2><ul>{advice}</ul>
<h2>إمتى لازم تروح للدكتور</h2><ul>{refer}</ul>
<p class="box">⚠️ هذا التقرير ناتج عن نظام دعم قرار تعليمي (مشروع تخرج - كلية الصيدلة) ولا يغني عن الكشف الطبي أو استشارة الصيدلي.</p>
</body></html>"""
