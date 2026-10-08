"""Pathway migration planner.

A deterministic, explainable engine. It turns a reviewed profile, the person's migration
circumstances, the versioned rulebook and live public signals into:

* a points breakdown at any date (age and experience move with time),
* per-visa criteria checks (met / not met / unknown / later),
* several dated strategies to permanent residence with milestones, costs and risks,
* a decision tree with the person's answers highlighted,
* a deadline register.

Nothing here is a visa decision. Every estimate states its assumptions.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Any

import migration_rules as R

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def add_months(d: date, months: float) -> date:
    whole = int(months)
    extra_days = int(round((months - whole) * 30.4))
    month = d.month - 1 + whole
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day) + timedelta(days=extra_days)


def months_between(a: date, b: date) -> float:
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.4


def iso(d: date | None):
    return d.isoformat() if d else None


def label(d: date | None):
    return d.strftime("%b %Y") if d else "Date unknown"


def age_on(dob: date | None, on: date) -> int | None:
    if not dob:
        return None
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def birthday(dob: date, age: int) -> date:
    try:
        return dob.replace(year=dob.year + age)
    except ValueError:  # 29 February
        return date(dob.year + age, 3, 1)


# ---------------------------------------------------------------------------
# Profile interpretation
# ---------------------------------------------------------------------------

def visa_code(text: str) -> str:
    v = (text or "").lower()
    if not v.strip():
        return "unknown"
    if "citizen" in v and "australian" in v:
        return "citizen"
    if "permanent resident" in v:
        return "pr"
    if "offshore" in v or "no current australian visa" in v:
        return "offshore"
    if "unsure" in v:
        return "unknown"
    if "bridging" in v:
        return "bridging"
    match = re.search(r"subclass\s*(\d{3})", v) or re.search(r"\b(\d{3})\b", v)
    if match:
        return match[1]
    if "student" in v:
        return "500"
    if "graduate" in v:
        return "485"
    return "other"


SETTLED = {"citizen", "pr", "189", "190", "191", "186", "858", "801", "100"}


def occupation_family(profile: dict) -> str:
    text = " ".join(str(profile.get(k) or "") for k in ("occupation", "careerFamily", "education")).lower()
    code = str(profile.get("anzsco") or "")
    if code.startswith("233") or code.startswith("2331") or re.search(r"engineer|mechatronic|robotic", text) and not re.search(r"software|data|network|cloud|devops", text):
        return "engineering"
    if code.startswith("261") or code.startswith("262") or code.startswith("263") or re.search(r"software|developer|\bict\b|\bit\b|information technology|computer science|computing|data scien|data analy|cyber|network|cloud|programmer", text):
        return "ict"
    if code.startswith("2211") or re.search(r"accountant|accounting|auditor", text):
        return "accounting"
    if code.startswith("254") or re.search(r"nurse|nursing|midwi", text):
        return "nursing"
    if code.startswith("241") or re.search(r"teacher|teaching", text):
        return "teaching"
    if re.search(r"electrician|plumber|carpenter|chef|cook|mechanic|fitter|welder|trade", text):
        return "trades"
    return "other"


def state_of(location: str) -> str:
    text = (location or "").upper()
    for code, info in R.STATES.items():
        if re.search(rf"\b{code}\b", text) or info["name"].upper() in text:
            return code
    return "QLD" if "BRISBANE" in text else ""


DEFAULT_CIRCUMSTANCES = {
    "dob": "", "passport": "", "qualification": "", "auQualification": None, "institution": "", "studyState": "",
    "studyRegional": "no", "courseCompletion": "", "australianStudy": None, "specialistEducation": False,
    "englishLevel": "", "englishTestDate": "", "skillsAssessment": "", "skillsAssessmentDate": "",
    "auExperienceYears": 0, "overseasExperienceYears": 0, "employedInOccupation": "", "stateEmploymentMonths": 0,
    "regionalEmploymentMonths": 0, "professionalYear": False, "naati": False, "partner": "", "partnerRelationship": "",
    "relationshipMonths": 0, "regional": "", "preferredStates": [], "employer": "", "salary": None,
    "sponsorMonths": 0, "currentVisaGrantDate": "", "targetPoints": None, "fieldOfStudy": "",
}


class Ctx:
    def __init__(self, profile: dict, circumstances: dict, live: dict | None = None, today: date | None = None):
        self.profile = profile or {}
        c = {**DEFAULT_CIRCUMSTANCES, **{k: v for k, v in (circumstances or {}).items() if v is not None or k in ("auQualification", "australianStudy", "salary")}}
        self.c = c
        self.live = live or {}
        self.today = today or date.today()
        self.visa_text = self.profile.get("visa") or ""
        self.visa = visa_code(self.visa_text)
        self.visa_expiry = parse_date(self.profile.get("visaExpiry"))
        self.dob = parse_date(c.get("dob"))
        self.occupation = (self.profile.get("occupation") or "").strip() or "your occupation"
        self.anzsco = str(self.profile.get("anzsco") or "").strip()
        field = (c.get("fieldOfStudy") or "").lower()
        self.field = field if field in R.FIELD_TO_ASSESSOR else occupation_family(self.profile)
        self.family = R.FIELD_TO_ASSESSOR[self.field]
        self.assessor = R.ASSESSORS[self.family]
        self.home_state = state_of(self.profile.get("location") or "")
        prefs = [s for s in (c.get("preferredStates") or []) if s in R.STATES]
        self.states = prefs or ([self.home_state] if self.home_state else ["QLD"])
        self.qualification = c.get("qualification") or self._guess_qualification()
        self.au_qualification = c.get("auQualification")
        if self.au_qualification is None:
            self.au_qualification = self.visa in {"500", "485"} or None
        self.completion = parse_date(c.get("courseCompletion"))
        self.assumptions: list[str] = []
        if not self.completion and self.visa == "500":
            if self.visa_expiry:
                self.completion = add_months(self.visa_expiry, -2)
                self.assumptions.append(f"Course completion assumed about 2 months before your visa expiry ({label(self.completion)}). Add the real date to sharpen every milestone.")
            else:
                self.completion = add_months(self.today, 6)
                self.assumptions.append("Course completion assumed 6 months from today because no completion date or visa expiry was supplied.")
        self.english = (c.get("englishLevel") or "").lower()
        passport = (c.get("passport") or "").strip().lower()
        self.english_exempt_passport = passport in R.ENGLISH_EXEMPT_PASSPORTS
        if not self.english and self.english_exempt_passport:
            self.english = "competent"
        self.assessment = (c.get("skillsAssessment") or "").lower()
        self.au_exp = float(c.get("auExperienceYears") or 0)
        self.os_exp = float(c.get("overseasExperienceYears") or 0)
        employed = (c.get("employedInOccupation") or "").lower()
        self.employed = employed == "yes"
        if self.employed:
            self.work_start = self.today
        else:
            base = max(self.today, self.completion or self.today)
            self.work_start = add_months(base, 3)
            self.assumptions.append(f"Skilled employment assumed to start around {label(self.work_start)} (about 3 months after {'graduation' if self.completion and self.completion >= self.today else 'today'}). The Jobs tab shows current openings.")
        self.partner = c.get("partner") or ""
        self.regional = (c.get("regional") or "").lower()
        emp = (c.get("employer") or "").lower()
        self.employer = "yes" if emp in {"yes", "offer", "sponsoring", "interested"} else "no" if emp in {"no", "none"} else ""
        self.salary = c.get("salary")

    def _guess_qualification(self):
        edu = (self.profile.get("education") or "").lower()
        if re.search(r"phd|doctor", edu): return "doctorate"
        if re.search(r"master.*research|mphil", edu): return "masters_research"
        if "master" in edu: return "masters_coursework"
        if "bachelor" in edu or "honours" in edu: return "bachelor"
        if "diploma" in edu: return "diploma"
        if "certificate" in edu: return "trade"
        return ""

    def age(self, on: date | None = None):
        return age_on(self.dob, on or self.today)

    def experience_at(self, on: date):
        gained = max(0.0, months_between(max(self.work_start, self.today), on) / 12) if on > self.work_start else 0.0
        return self.au_exp + gained, self.os_exp

    def fee(self, code):
        live = (self.live.get("fees") or {}).get(code)
        if live and live.get("amount"):
            return live["amount"], "live", live
        return R.VISAS[code]["fee"], "rulebook", None

    def round(self):
        return (self.live.get("round") or {})

    def round_minimum(self):
        r = self.round()
        return r.get("minimumPoints") if r.get("occupationStatus") == "published" else None

    def target_189(self):
        """Live published minimum first; otherwise a target the person set themselves."""
        live = self.round_minimum()
        if live is not None:
            return live, "live"
        own = self.c.get("targetPoints")
        try:
            own = int(own) if own not in (None, "") else None
        except (TypeError, ValueError):
            own = None
        return (own, "user") if own else (None, None)


# ---------------------------------------------------------------------------
# Points
# ---------------------------------------------------------------------------

def _age_points(age):
    if age is None:
        return None
    return next((p for lo, hi, p in R.AGE_POINTS if lo <= age <= hi), 0)


def _exp_points(au, os_):
    au_p = next((p for yrs, p in R.AU_EXPERIENCE_POINTS if au >= yrs), 0)
    os_p = next((p for yrs, p in R.OS_EXPERIENCE_POINTS if os_ >= yrs), 0)
    return au_p, os_p, min(R.EXPERIENCE_CAP, au_p + os_p)


def points_at(ctx: Ctx, on: date | None = None, nomination: str | None = None, overrides: dict | None = None):
    on = on or ctx.today
    o = overrides or {}
    c = ctx.c
    rows = []

    def row(fid, lbl, pts, mx, basis, status="claimed", improve=None):
        rows.append({"id": fid, "label": lbl, "points": pts or 0, "max": mx, "basis": basis, "status": status if pts is not None else "unknown", "improve": improve})

    age = ctx.age(on)
    ap = _age_points(age)
    nxt = None
    if ctx.dob and age is not None:
        for cliff in (25, 33, 40, 45):
            if age < cliff:
                nxt = cliff
                break
    row("age", "Age", ap, 30, f"Age {age} on {label(on)}" + (f"; changes at {nxt} ({label(birthday(ctx.dob, nxt))})" if nxt else "") if age is not None else "Add your date of birth", improve=None)

    eng = o.get("english", ctx.english)
    ep = R.ENGLISH_POINTS.get(eng)
    row("english", "English", ep, 20, {"competent": "Competent English: 0 points (threshold only)", "proficient": "Proficient English", "superior": "Superior English"}.get(eng, "No points-test English result recorded"),
        status="claimed" if ep is not None else "unknown",
        improve={"proficient": "Superior English adds 10 more", "competent": "Proficient adds 10; Superior adds 20", "superior": None}.get(eng, "Sit IELTS or PTE: Proficient = 10, Superior = 20"))

    au, os_ = ctx.experience_at(on)
    au = o.get("auExperience", au)
    au_p, os_p, total_exp = _exp_points(au, os_)
    row("experience", "Skilled employment", total_exp, 20,
        f"{au:.1f} years Australian ({au_p}) + {os_:.1f} years overseas ({os_p}), capped at 20. Must be assessed as skilled, 20+ hours a week, in the last 10 years.",
        improve="Australian experience: 1 yr = 5, 3 yrs = 10, 5 yrs = 15, 8 yrs = 20")

    q = ctx.qualification
    qp = R.QUALIFICATION_POINTS.get(q)
    row("qualification", "Qualification", qp, 20, {"doctorate": "Doctorate", "masters_research": "Masters (15, same as bachelor)", "masters_coursework": "Masters (15, same as bachelor)", "bachelor": "Bachelor or higher", "diploma": "Diploma", "trade": "Trade qualification"}.get(q, "Confirm your highest qualification"))

    ast = o.get("australianStudy", c.get("australianStudy"))
    if ast is None:
        ast = bool(ctx.au_qualification and q in {"bachelor", "masters_coursework", "masters_research", "doctorate"})
    row("australianStudy", "Australian study requirement", 5 if ast else 0, 5, "At least 2 academic years (92 weeks) of CRICOS study in Australia" if ast else "Not claimed")
    spec = o.get("specialistEducation", c.get("specialistEducation"))
    row("specialist", "Specialist education (STEM research masters or PhD)", 10 if spec else 0, 10, "Australian research masters or doctorate in STEM, 2+ academic years" if spec else "Not claimed")
    py = o.get("professionalYear", c.get("professionalYear"))
    row("professionalYear", "Professional Year", 5 if py else 0, 5, "Completed in the last 4 years" if py else ("Available for engineering, ICT and accounting" if ctx.assessor.get("professionalYear") else "Not offered for this occupation"),
        improve="12 month program; about 44 weeks including an internship" if not py and ctx.assessor.get("professionalYear") else None)
    naati = o.get("naati", c.get("naati"))
    row("naati", "Credentialed community language (NAATI CCL)", 5 if naati else 0, 5, "NAATI CCL passed" if naati else "Not claimed", improve="One test in a language you speak (for example Vietnamese)" if not naati else None)
    reg = o.get("regionalStudy", c.get("studyRegional") in {"yes", "cat2", "cat3"})
    row("regionalStudy", "Study in regional Australia", 5 if reg else 0, 5, "Studied and lived in a designated regional area for 2 academic years" if reg else "Not claimed")
    partner = o.get("partner", ctx.partner)
    pp = R.PARTNER_POINTS.get(partner)
    row("partner", "Partner", pp, 10, {"single": "Single", "partner_citizen_pr": "Partner is an Australian citizen or PR", "partner_skilled": "Skilled partner: under 45, competent English, positive assessment",
                                      "partner_competent_english": "Partner has competent English", "partner_other": "Partner cannot be claimed"}.get(partner, "Add relationship status"),
        improve="A partner with competent English adds 5; a skilled partner adds 10" if partner == "partner_other" else None)
    if nomination:
        row("nomination", f"Nomination ({nomination})", R.NOMINATION_POINTS[nomination], R.NOMINATION_POINTS[nomination], "State or territory nomination" if nomination == "190" else "Regional nomination or family sponsorship")
    total = sum(r["points"] for r in rows)
    unknown = [r["label"] for r in rows if r["status"] == "unknown"]
    return {"total": total, "date": iso(on), "rows": rows, "unknown": unknown, "passMark": R.PASS_MARK, "age": age}


def points_timeline(ctx: Ctx, months=72, step=3):
    """Points without nomination over time: experience accrues, age bands change."""
    rows, d = [], ctx.today
    for _ in range(0, months + 1, step):
        p = points_at(ctx, d)
        rows.append({"date": iso(d), "label": d.strftime("%b %Y"), "points": p["total"], "age": p["age"],
                     "with190": p["total"] + 5, "with491": p["total"] + 15})
        d = add_months(d, step)
    return rows


def points_options(ctx: Ctx):
    """What-if choices for the points lab, each with the value already recorded so the simulator starts from it."""
    base = {r["id"]: r for r in points_at(ctx)["rows"]}
    au, os_ = ctx.au_exp, ctx.os_exp
    au_opts = sorted({round(au, 1), 1, 3, 5, 8} - {x for x in (1, 3, 5, 8) if x < au})
    yes_no = lambda pts, yes="Yes": [{"value": False, "label": "No", "points": 0}, {"value": True, "label": yes, "points": pts}]
    return [
        {"id": "english", "factor": "english", "label": "English", "current": ctx.english if ctx.english in R.ENGLISH_POINTS else None,
         "choices": [{"value": k, "label": k.title(), "points": v, "detail": R.ENGLISH_LEVELS[k]} for k, v in R.ENGLISH_POINTS.items()]},
        {"id": "auExperience", "factor": "experience", "label": "Australian skilled employment", "current": round(au, 1),
         "choices": [{"value": y, "label": f"{y:g} yrs", "points": _exp_points(y, os_)[2], "detail": f"Combined with {os_:g} overseas years, capped at 20"} for y in au_opts]},
        {"id": "australianStudy", "factor": "australianStudy", "label": "Australian study (2 academic years)", "current": base["australianStudy"]["points"] > 0, "choices": yes_no(5, "Met")},
        {"id": "regionalStudy", "factor": "regionalStudy", "label": "Studied at a regional campus", "current": base["regionalStudy"]["points"] > 0, "choices": yes_no(5)},
        {"id": "professionalYear", "factor": "professionalYear", "label": "Professional Year", "available": bool(ctx.assessor.get("professionalYear")), "current": bool(ctx.c.get("professionalYear")), "choices": yes_no(5, "Completed")},
        {"id": "naati", "factor": "naati", "label": "NAATI CCL", "current": bool(ctx.c.get("naati")), "choices": yes_no(5, "Passed")},
        {"id": "specialistEducation", "factor": "specialist", "label": "STEM research degree in Australia", "current": bool(ctx.c.get("specialistEducation")), "choices": yes_no(10, "Completed")},
        {"id": "partner", "factor": "partner", "label": "Partner", "current": ctx.partner or None,
         "choices": [{"value": k, "label": l, "points": R.PARTNER_POINTS[k]} for k, l in (("single", "Single"), ("partner_citizen_pr", "Citizen or PR partner"), ("partner_skilled", "Skilled partner"), ("partner_competent_english", "Partner competent English"), ("partner_other", "Partner, no claim"))]},
        {"id": "nomination", "factor": None, "label": "Nomination", "current": "",
         "choices": [{"value": "", "label": "None (189)", "points": 0}, {"value": "190", "label": "190 state", "points": 5}, {"value": "491", "label": "491 regional", "points": 15}]},
    ]


# ---------------------------------------------------------------------------
# Criteria checks
# ---------------------------------------------------------------------------

def crit(cid, lbl, state, detail="", fix=None):
    return {"id": cid, "label": lbl, "state": state, "detail": detail, "fix": fix}


def english_state(ctx, needed="competent"):
    order = ["vocational", "competent", "proficient", "superior"]
    if ctx.english_exempt_passport and needed == "competent":
        return "met", "Exempt passport counts as competent English"
    if not ctx.english or ctx.english == "none":
        return "unknown", "No current test result recorded"
    if ctx.english not in order:
        return "unknown", "Level not recognised"
    return ("met" if order.index(ctx.english) >= order.index(needed) else "unmet"), f"Recorded level: {ctx.english}"


def assessment_state(ctx):
    a = ctx.assessment
    if a == "positive":
        return "met", f"Positive assessment recorded ({ctx.assessor['name']})"
    if a in {"submitted", "planned"}:
        return "later", f"{ctx.assessor['name']} assessment {a}"
    return "unmet" if a == "none" else "unknown", f"{ctx.assessor['name']} assesses {ctx.occupation}"


def age_state(ctx, limit, on=None):
    a = ctx.age(on)
    if a is None:
        return "unknown", "Add date of birth"
    return ("met" if a < limit else "unmet"), f"Age {a}" + (f" on {label(on)}" if on else "")


def visa_checks(ctx: Ctx, code: str, pts_now: int) -> list[dict]:
    c = ctx.c
    rows = []
    if code == "485":
        a = ctx.age()
        exception = ctx.qualification in {"masters_research", "doctorate"} or (c.get("passport") or "").lower() in {"hong kong", "bno", "british national (overseas)"}
        rows.append(crit("age", "Under 35 when you apply" + (" (research masters, PhD and HK/BNO: under 50)" if exception else ""), "unknown" if a is None else "met" if a < (50 if exception else 35) else "unmet", f"Age {a}" if a is not None else "Add date of birth"))
        rows.append(crit("student", "Held a student visa in the last 6 months", "met" if ctx.visa == "500" else "met" if ctx.visa == "485" else "unknown", ctx.visa_text or "Current visa not set"))
        rows.append(crit("study", "Completed 2 academic years of CRICOS study (at least 16 calendar months)", "met" if ctx.au_qualification else "unknown", "Recorded as Australian study" if ctx.au_qualification else "Confirm your course is CRICOS registered and 2 years long"))
        rows.append(crit("qualification", "Bachelor, masters or doctorate (Post-Higher Education stream)", "met" if ctx.qualification in {"bachelor", "masters_coursework", "masters_research", "doctorate"} else "unknown", ctx.qualification or "Confirm qualification"))
        e, d = english_state(ctx, "competent")
        rows.append(crit("english", "English: " + R.ENGLISH_485, "met" if ctx.english_exempt_passport else ("later" if e != "unmet" else "unmet"), "485 uses its own test rules: a result taken within 12 months, single in-centre sitting" if not ctx.english_exempt_passport else d))
        rows.append(crit("timing", "Lodge in Australia within 6 months of course completion", "later" if ctx.completion and ctx.completion >= ctx.today else ("met" if ctx.completion and months_between(ctx.completion, ctx.today) <= 6 else "unknown" if not ctx.completion else "unmet"), f"Completion {label(ctx.completion)}" if ctx.completion else "Add completion date"))
        rows.append(crit("health", "Overseas Visitor Health Cover and police certificates", "later", "Arrange before lodging. OSHC does not satisfy this."))
    elif code in {"189", "190", "491"}:
        e, d = english_state(ctx, "competent")
        a_state, a_detail = assessment_state(ctx)
        nom = R.NOMINATION_POINTS.get(code, 0)
        target = ctx.round_minimum() if code == "189" else None
        rows += [crit("age", "Under 45 when invited", *age_state(ctx, 45)),
                 crit("english", "At least competent English", e, d, "Book IELTS or PTE"),
                 crit("assessment", "Positive skills assessment for the nominated occupation", a_state, a_detail, f"Apply to {ctx.assessor['name']}"),
                 crit("points", f"At least {R.PASS_MARK} points" + (f" including {nom} nomination points" if nom else ""), "met" if pts_now + nom >= R.PASS_MARK else "unmet", f"{pts_now + nom} points today")]
        if code == "189":
            r = ctx.round()
            if target is not None:
                rows.append(crit("competitive", f"Competitive with the latest published minimum ({target} in {r.get('date')})", "met" if pts_now >= target else "unmet", f"{pts_now} vs {target}. A published minimum is history, not a forecast."))
            elif r.get("date"):
                rows.append(crit("competitive", f"Occupation invited in the latest round ({r.get('date')})", "unmet", f"{ctx.occupation} had no published row in that round. 189 invitations for it are uncertain."))
            else:
                rows.append(crit("competitive", "Latest invitation round evidence", "unknown", "Home Affairs round data unavailable right now"))
            rows.append(crit("list", "Occupation on the MLTSSL", "unknown" if not ctx.anzsco else "later", "Confirm with the skilled occupation list for your ANZSCO code"))
        else:
            rows.append(crit("nomination", "State or territory nomination" if code == "190" else "Regional nomination or eligible family sponsorship", "later", "Meet the chosen state's stream criteria and wait for an invitation"))
            if code == "491":
                rows.append(crit("regional", "Willing to live and work in a designated regional area for 3 years", "met" if ctx.regional == "yes" else "unmet" if ctx.regional == "no" else "unknown", {"yes": "You said yes", "no": "You said no", "maybe": "You said maybe"}.get(ctx.regional, "Not answered")))
    elif code == "482":
        exp_now = ctx.au_exp + ctx.os_exp
        rows += [crit("employer", "Approved employer willing to nominate you", {"yes": "met", "no": "unmet"}.get(ctx.employer, "unknown"), {"yes": "You have a sponsoring employer", "no": "No sponsoring employer"}.get(ctx.employer, "Not answered")),
                 crit("experience", "At least 1 year of relevant work experience", "met" if exp_now >= 1 else "later", f"{exp_now:g} years recorded"),
                 crit("salary", f"Core Skills: salary at least ${R.CSIT:,} and the market rate", "met" if ctx.salary and ctx.salary >= R.CSIT else "unmet" if ctx.salary else "unknown", f"${ctx.salary:,.0f} recorded" if ctx.salary else "Add expected salary"),
                 crit("english", "English (Core Skills generally IELTS 5 overall or equivalent)", "met" if ctx.english in {"competent", "proficient", "superior"} or ctx.english_exempt_passport else "unknown", ""),
                 crit("list", "Occupation on the Core Skills Occupation List", "unknown", "Check the CSOL for your occupation")]
    elif code == "186":
        exp_total = ctx.au_exp + ctx.os_exp
        a_state, a_detail = assessment_state(ctx)
        e, d = english_state(ctx, "competent")
        rows += [crit("age", "Under 45 at application (some exemptions)", *age_state(ctx, 45)),
                 crit("english", "Competent English", e, d),
                 crit("trt", "Transition: 2 years working for an approved sponsor on 482", "met" if float(ctx.c.get("sponsorMonths") or 0) >= 24 else "later" if ctx.visa == "482" else "unmet", f"{ctx.c.get('sponsorMonths') or 0} months with sponsor recorded"),
                 crit("de", "Direct Entry: 3 years of relevant experience and a positive assessment", "met" if exp_total >= 3 and a_state == "met" else "later", f"{exp_total:g} years, assessment {ctx.assessment or 'not recorded'}"),
                 crit("employer", "Employer nomination at or above CSIT and market rate", {"yes": "met", "no": "unmet"}.get(ctx.employer, "unknown"), "")]
    elif code == "494":
        exp_total = ctx.au_exp + ctx.os_exp
        a_state, a_detail = assessment_state(ctx)
        rows += [crit("age", "Under 45", *age_state(ctx, 45)),
                 crit("experience", "3 years of full-time skilled experience", "met" if exp_total >= 3 else "later", f"{exp_total:g} years recorded"),
                 crit("assessment", "Positive skills assessment", a_state, a_detail),
                 crit("employer", "Regional employer willing to sponsor", {"yes": "later", "no": "unmet"}.get(ctx.employer, "unknown"), "Your employer must be in a designated regional area"),
                 crit("regional", "Live and work in a designated regional area", "met" if ctx.regional == "yes" else "unmet" if ctx.regional == "no" else "unknown", "")]
    elif code == "191":
        rows += [crit("held", "Held 491 or 494 for 3 years while complying with regional conditions", "met" if ctx.visa in {"491", "494"} and parse_date(ctx.c.get("currentVisaGrantDate")) and months_between(parse_date(ctx.c.get("currentVisaGrantDate")), ctx.today) >= 36 else "later", ""),
                 crit("tax", "ATO notices of assessment for 3 income years", "later", "Lodge every tax return on time")]
    elif code == "820":
        p = ctx.partner == "partner_citizen_pr"
        rel = ctx.c.get("partnerRelationship")
        months = float(ctx.c.get("relationshipMonths") or 0)
        rows += [crit("sponsor", "Partner is an Australian citizen, PR or eligible NZ citizen", "met" if p else "unmet" if ctx.partner else "unknown", ""),
                 crit("relationship", "Married, registered, or de facto for 12 months", "met" if rel in {"married", "registered"} or months >= 12 else "later" if p else "unknown", f"{rel or 'relationship'} · {months:g} months"),
                 crit("8503", "No 'No Further Stay' (8503) condition", "unknown", "Check VEVO")]
    return rows


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, ctx: Ctx, sid: str):
        self.ctx, self.sid = ctx, sid
        self.milestones: list[dict] = []
        self.lanes: list[dict] = []
        self.costs: list[dict] = []
        self.risks: list[dict] = []
        self.assumptions: list[str] = []

    def m(self, mid, title, start, end=None, kind="step", detail="", tasks=(), cost=None, sources=(), visa=None, uncertain=False, deadline=None):
        start = start or self.ctx.today
        end = end or start
        status = "done" if end < self.ctx.today else "now" if start <= self.ctx.today <= end or (start - self.ctx.today).days < 45 else "upcoming"
        self.milestones.append({"id": f"{self.sid}:{mid}", "title": title, "start": iso(start), "end": iso(end), "kind": kind, "detail": detail,
                                "tasks": [dict(t, id=f"{self.sid}:{mid}:{i}") for i, t in enumerate(tasks)], "cost": cost, "sources": [{"label": l, "url": u} for l, u in sources],
                                "visa": visa, "uncertain": uncertain, "status": status, "deadline": iso(deadline) if deadline else None})
        return end

    def lane(self, code, start, end, kind="held", note=""):
        if start and end and end > start:
            self.lanes.append({"code": code, "label": f"{code} {R.VISAS.get(code, {}).get('name', '')}".strip(), "start": iso(start), "end": iso(end), "kind": kind, "note": note})

    def fee(self, code, label_=None):
        amount, basis, live = self.ctx.fee(code)
        self.costs.append({"label": label_ or f"Subclass {code} visa charge", "amount": amount, "kind": "government", "basis": basis,
                           "note": R.VISAS[code].get("feeNote", "Primary applicant base charge from 1 July 2026"), "checkedAt": (live or {}).get("checkedAt")})

    def approx(self, key, label_=None):
        lo, hi, note = R.APPROX_COSTS[key]
        self.costs.append({"label": label_ or note.split(" (")[0], "amount": lo, "amountHigh": hi, "kind": "approx", "note": note})


def task(lbl, detail="", link=None, action=None):
    t = {"label": lbl}
    if detail: t["detail"] = detail
    if link: t["link"] = link
    if action: t["action"] = action
    return t


def jobs_action(ctx, role=None, location=None, note=""):
    return {"type": "jobs", "role": role or ctx.profile.get("occupation") or "", "location": location or ctx.profile.get("location") or "Australia", "note": note}


def prepare_basics(b: Builder, need_points_english=True, deadline=None):
    """English and skills assessment milestones shared by points-tested routes."""
    ctx = b.ctx
    ready = ctx.today
    if ctx.assessment != "positive":
        start = max(ctx.today, ctx.completion or ctx.today) if ctx.au_qualification else ctx.today
        weeks = ctx.assessor["weeks"]
        end = start + timedelta(weeks=weeks[1])
        opt = ctx.assessor["options"][0]
        b.m("assessment", f"Skills assessment with {ctx.assessor['name']}", start, end, "assessment",
            f"Assess as {ctx.occupation}. Typical decision {weeks[0]} to {weeks[1]} weeks. Outcomes are generally valid for 3 years for points-tested visas." +
            (" Graduates of an accredited Australian degree use the simplest pathway once the degree is conferred." if ctx.family == "engineering" and ctx.au_qualification else ""),
            [task("Collect testamur, academic transcript and completion letter"), task("Write duties for any employment you want assessed as skilled (dates, hours, duties, references)"),
             task(f"Lodge with {ctx.assessor['name']}", link=ctx.assessor["url"]), task("Ask for skilled employment to be assessed so it can earn points")],
            cost={"amount": opt[1], "label": opt[0]}, sources=[(ctx.assessor["name"], ctx.assessor["url"]), *[R.SECONDARY["assessment_fees"]]])
        b.costs.append({"label": f"{ctx.assessor['name']}: {opt[0]}", "amount": opt[1], "kind": "assessment", "note": "Indicative fee"})
        ready = max(ready, end)
    if need_points_english and ctx.english not in {"proficient", "superior"}:
        start = ctx.today
        end = add_months(start, 2)
        b.m("english", "English test for points: aim for Superior", start, end, "test",
            f"Competent is the minimum (0 points). Proficient adds 10, Superior adds 20. {R.ENGLISH_LEVELS['superior']}. Results count for 3 years for points.",
            [task("Take a diagnostic mock test to pick IELTS or PTE"), task("Book the test with enough time for a resit", link=R.ENGLISH_URL), task("Record your scores in Pathway to update points")],
            cost={"amount": R.APPROX_COSTS["englishTest"][0], "label": "Approximate test fee", "approx": True}, sources=[("Home Affairs English requirements", R.ENGLISH_URL), R.SECONDARY["pte"]])
        b.approx("englishTest", "English test (points)")
        ready = max(ready, end)
    return ready


def graduate_bridge(b: Builder):
    """Student to 485. Returns (grant_estimate, expiry_estimate) or (None, coverage_end)."""
    ctx = b.ctx
    if ctx.visa == "485":
        exp = ctx.visa_expiry
        if exp:
            b.lane("485", ctx.today, exp, "held", "Current visa")
        return None, exp
    if ctx.visa != "500":
        if ctx.visa_expiry:
            b.lane(ctx.visa if ctx.visa in R.VISAS else "current", ctx.today, ctx.visa_expiry, "held", ctx.visa_text)
        return None, ctx.visa_expiry
    comp = ctx.completion
    start500 = ctx.today
    b.lane("500", start500, ctx.visa_expiry or add_months(comp, 2), "held", "Current visa")
    deadline = add_months(comp, 6)
    if ctx.visa_expiry and ctx.visa_expiry < deadline:
        deadline_note = f"Your student visa expires {label(ctx.visa_expiry)}, before the 6 month window closes. Lodge while you still hold it."
        deadline = ctx.visa_expiry
    else:
        deadline_note = "Lodge within 6 months of the completion date on your completion letter, while you hold a visa."
    if deadline < ctx.today:
        b.risks.append({"level": "high", "title": "The 485 window has closed", "detail": f"Your course completed {label(comp)}, so the 6 month window to lodge a 485 ended {label(deadline)}. If you already lodged or hold a 485, change your visa on the profile so the plan starts from it."})
        return None, ctx.visa_expiry
    a = ctx.age(deadline)
    exception = ctx.qualification in {"masters_research", "doctorate"}
    eligible = (a is None or a < (50 if exception else 35)) and ctx.qualification in {"bachelor", "masters_coursework", "masters_research", "doctorate", ""}
    b.m("complete", "Finish your course and get the completion letter", comp, comp, "study",
        "The completion letter date starts the 485 clock. Your student visa usually stays valid for a short period after the course ends; work hours are unlimited after completion while it is valid.",
        [task("Request the official completion letter from your university"), task("Keep satisfactory attendance and progress until the end"), task("Check your visa expiry and conditions on VEVO", link=R.VEVO_URL)],
        sources=[("Subclass 500", R.VISA_URL["500"])])
    if not eligible:
        b.risks.append({"level": "high", "title": "Temporary Graduate visa looks unavailable", "detail": "Age, a previous 485 grant or the qualification type appears to rule out the Post-Higher Education stream. Plan another visa before your student visa ends."})
        return None, ctx.visa_expiry
    eng_start = max(ctx.today, add_months(comp, -3))
    b.m("english485", "English test for the 485", eng_start, max(eng_start, add_months(comp, 1)), "test",
        R.ENGLISH_485 + ". A points-test result (Proficient or Superior) also satisfies this if it is recent and from a single sitting.",
        [task("Book an in-centre IELTS or PTE sitting (online tests are not accepted)", link=R.ENGLISH_URL), task("Aim for Superior so the same result can earn 20 points later")],
        cost={"amount": R.APPROX_COSTS["englishTest"][0], "label": "Approximate test fee", "approx": True}, sources=[R.SECONDARY["485"]])
    lodge = max(ctx.today, comp + timedelta(days=21))
    if lodge > deadline:
        lodge = deadline
    b.m("lodge485", "Lodge the Temporary Graduate (485) application", lodge, deadline, "apply",
        deadline_note + " Lodging inside Australia gives you a bridging visa that generally carries the 485's full work rights until a decision (check VEVO).",
        [task("Buy Overseas Visitor Health Cover (OSHC does not count)"), task("Apply for police certificates (Australia and any country lived in 12+ months since age 16)"),
         task("Lodge in ImmiAccount while in Australia", link=R.VISA_URL["485"]), task("Book the health examination when requested")],
        cost={"amount": ctx.fee("485")[0], "label": "485 visa charge"}, sources=[("Subclass 485", R.VISA_URL["485"]), R.SECONDARY["485"]], visa="485", deadline=deadline)
    b.fee("485")
    b.approx("ovhc", "Overseas Visitor Health Cover (first year)")
    lo, hi = R.VISAS["485"]["processingMonths"]
    grant = add_months(lodge, (lo + hi) / 2)
    years = 3 if ctx.qualification in {"masters_research", "doctorate"} else 2
    expiry = add_months(grant, years * 12)
    b.lane("BVA", lodge, grant, "processing", "Bridging visa while 485 is processed")
    b.lane("485", grant, expiry, "projected", f"{years} years from grant")
    b.m("grant485", f"485 granted: {years} years of full work rights", grant, grant, "visa",
        f"Estimated {lo} to {hi} months after lodgement. The stay runs from the grant date, so every month of skilled work from here counts toward points and employer routes.",
        [task("Start or continue skilled full-time work in your occupation", action=jobs_action(ctx, note="Roles that build assessable skilled employment")),
         task("Keep payslips, contract and a duties statement for every job")], visa="485", uncertain=True)
    if ctx.c.get("studyRegional") in {"yes", "cat2", "cat3"}:
        extra = 1
        b.m("second485", "Second 485 option: 1 to 2 more years", add_months(expiry, -3), expiry, "visa",
            "You studied at a regional campus. If you also live in a regional area while on your first 485 you may qualify for the second Post-Higher Education stream ($2,265): 1 extra year in places like the Gold Coast or Sunshine Coast, 2 in other regional areas. The timeline counts 1 year to stay conservative.",
            [task("Keep living in the regional area and keep evidence of address")], visa="485", uncertain=True)
        expiry = add_months(expiry, extra * 12)
    return grant, expiry


def competitive_date(ctx: Ctx, start: date, target: int | None, nomination=None, horizon_months=84):
    """First month from start where points reach target while under 45."""
    if target is None:
        return None, None
    d = start
    for _ in range(horizon_months):
        a = ctx.age(d)
        if a is not None and a >= 45:
            return None, None
        p = points_at(ctx, d, nomination)["total"]
        if p >= target:
            return d, p
        d = add_months(d, 1)
    return None, None


def boosters(ctx: Ctx):
    items = []
    if ctx.english != "superior":
        gain = 20 - R.ENGLISH_POINTS.get(ctx.english, 0)
        items.append({"id": "english", "label": "Reach Superior English", "points": gain, "time": "1 to 3 months", "cost": "About $410 to $480 per sitting"})
    if ctx.assessor.get("professionalYear") and not ctx.c.get("professionalYear"):
        items.append({"id": "professionalYear", "label": "Complete a Professional Year", "points": 5, "time": "About 12 months", "cost": "About $10,000 to $16,000"})
    if not ctx.c.get("naati"):
        items.append({"id": "naati", "label": "Pass NAATI CCL", "points": 5, "time": "1 to 3 months", "cost": "About $800 to $900"})
    if ctx.partner == "partner_other":
        items.append({"id": "partner", "label": "Partner earns competent English (5) or a positive assessment (10)", "points": 5, "time": "1 to 6 months", "cost": "Test or assessment fees"})
    return items


def strat_189(ctx: Ctx, pts_now):
    b = Builder(ctx, "s189")
    grant485, cover_end = graduate_bridge(b)
    ready = prepare_basics(b)
    target, target_basis = ctx.target_189()
    r = ctx.round()
    eoi_from = max(ready, ctx.today)
    comp_date, comp_pts = competitive_date(ctx, eoi_from, target)
    boost = boosters(ctx)
    boost_total = sum(x["points"] for x in boost)
    b.m("eoi", "Lodge your SkillSelect EOI (189)", eoi_from, eoi_from, "apply",
        f"Claim only points you can evidence on the invitation date. An EOI stays in the pool for 2 years. Points today: {pts_now}." +
        (f" Latest published minimum for your occupation: {target} ({r.get('date')})." if target else f" {ctx.occupation} was not listed in the latest published round." if r.get("date") else ""),
        [task("Create the EOI in SkillSelect", link=R.SKILLSELECT_URL), task("Select 189 (and 190/491 states if relevant) in one EOI"),
         task("Update the EOI whenever points rise (experience anniversaries, new test result)")],
        sources=[("SkillSelect", R.SKILLSELECT_URL), ("Points table", R.POINTS_TABLE_URL)])
    if comp_date:
        inv = add_months(comp_date, 1)
        b.m("competitive", f"Points reach {comp_pts} ({'latest published minimum' if target_basis == 'live' else 'your target'} {target})", comp_date, comp_date, "decision",
            "From here your EOI matches the last published minimum for your occupation. Rounds and minimums move; this is a signal, not a forecast.", uncertain=True)
    else:
        inv = None
    if inv:
        lodge_end = inv + timedelta(days=60)
        b.m("invite", "Invitation to apply (if issued)", inv, add_months(inv, 6), "visa", "Invitations are monthly-ish and depend on ranking within your occupation's ceiling. Lodge within 60 days.",
            [task("Prepare documents before the invitation: identity, assessment, English, employment evidence, police certificates"), task("Lodge the 189 within 60 days", link=R.VISA_URL["189"])],
            visa="189", uncertain=True)
        lo, hi = R.VISAS["189"]["processingMonths"]
        pr_lo, pr_hi = add_months(inv, 1 + lo), add_months(lodge_end, hi + 6)
        b.lane("BVA", inv + timedelta(days=30), pr_lo, "processing", "Bridging visa after lodging onshore")
        b.m("pr", "Permanent residence (189)", pr_lo, pr_hi, "pr", f"{R.VISAS['189']['processing']} after lodgement.", visa="189", uncertain=True)
        b.fee("189")
        b.approx("medical", "Health examination")
        b.approx("police", "Police certificates")
        pr_window = (pr_lo, pr_hi)
    else:
        pr_window = (None, None)
        b.fee("189", "Subclass 189 visa charge (if invited)")
    reasons, level = [], "Viable"
    a = ctx.age()
    if a is not None and a >= 45:
        level = "Not available"; reasons.append("Age 45 or over at invitation rules out 189.")
    elif target is None and r.get("date"):
        level = "Long shot"; reasons.append(f"{ctx.occupation} had no published invitation row in the {r.get('date')} round. Set your own target score in the Points lab to see a dated scenario.")
        if boost_total:
            reasons.append(f"Boosters could add up to {boost_total} points; keep the EOI active and watch future rounds.")
    elif target is None:
        level = "Needs evidence"; reasons.append("Invitation round data is unavailable right now, so competitiveness cannot be checked.")
    elif pts_now >= target:
        level = "Strong" if target_basis == "live" else "Viable"
        reasons.append(f"Your current {pts_now} points meet {'the latest published minimum' if target_basis == 'live' else 'your own target'} of {target}.")
    elif comp_date and (not cover_end or comp_date <= cover_end):
        level = "Viable"; reasons.append(f"Time-based points (experience) reach {target} around {label(comp_date)}, within your visa coverage.")
    elif comp_date:
        level = "Stretch"; reasons.append(f"You reach {target} around {label(comp_date)}, after your projected visa coverage ends ({label(cover_end)}).")
    else:
        level = "Stretch" if pts_now + boost_total >= target else "Long shot"
        reasons.append(f"Time alone does not reach {target}. Boosters available: +{boost_total}.")
    if cover_end and inv and inv > cover_end:
        b.risks.append({"level": "high", "title": "Visa gap before invitation", "detail": f"Projected coverage ends {label(cover_end)}. You would need a bridge such as a 482, a second 485 or lodging another substantive application."})
    if a is not None and ctx.dob:
        for cliff, drop in ((33, 5), (40, 10), (45, None)):
            day = birthday(ctx.dob, cliff)
            if ctx.today < day < (pr_window[0] or add_months(ctx.today, 60)):
                b.risks.append({"level": "high" if drop is None else "medium", "title": f"Age {cliff} on {label(day)}", "detail": ("Points-tested visas need you under 45 at invitation." if drop is None else f"Age points drop by {drop} on that date. Being invited before it protects them.")})
                break
    return finalize(b, "189", "Independent skilled PR", ["500", "485", "189"] if ctx.visa == "500" else [ctx.visa, "189"] if ctx.visa not in {"unknown", "189"} else ["189"],
                    "No employer or state ties. Highest control, but invitations are competitive per occupation.", level, reasons, pr_window,
                    dependencies=["Competitive points for your occupation", "Positive skills assessment", "Invitation"], points={"now": pts_now, "target": target, "targetBasis": target_basis, "competitiveDate": iso(comp_date), "boosters": boost},
                    flexibility="Highest: no employer or location obligation", obligation="None")


def state_stream(ctx: Ctx, state: str, kind: str):
    """Returns (ready_date, description, met_ties) for the state's onshore graduate or worker stream."""
    info = R.STATES[state]
    months = info.get("graduateMonths190" if kind == "190" else "graduateMonths491")
    grad_ties = ctx.au_qualification and (ctx.c.get("studyState") or ctx.home_state) == state
    if months:
        already = float(ctx.c.get("stateEmploymentMonths" if kind == "190" else "regionalEmploymentMonths") or 0)
        start = ctx.today if ctx.employed and (kind == "190" or ctx.regional == "yes") else ctx.work_start
        ready = add_months(start, max(0, months - already))
        where = "Queensland" if kind == "190" else "regional Queensland"
        desc = (f"{info['name']} graduate stream" if grad_ties else f"{info['name']} onshore skilled worker stream") + f": {months} months working in {where} at 20+ hours a week, immediately before the ROI"
        return ready, desc, True
    return ctx.today, f"{info['name']} streams change by program year; confirm ties (study, work or residence) required", grad_ties


def strat_190(ctx: Ctx, pts_now, state):
    b = Builder(ctx, f"s190{state.lower()}")
    info = R.STATES[state]
    grant485, cover_end = graduate_bridge(b)
    ready = prepare_basics(b)
    stream_ready, desc, ties = state_stream(ctx, state, "190")
    roi = max(ready, stream_ready)
    live_state = (ctx.live.get("states") or {}).get(state) or {}
    if stream_ready > ctx.today:
        b.m("statework", f"Build {info['name']} work history", max(ctx.today, ctx.work_start), stream_ready, "work", desc + ". Work must be after your qualification and match the first 3 digits of your occupation code (QLD) or the state's rule.",
            [task("Secure skilled work in the state", action=jobs_action(ctx, location=f"{info['name']}")), task("Keep hours above the state's minimum every week"), task("Collect payslips and a duties letter")],
            sources=[(info["name"] + " program", info["url"])])
    b.m("roi", f"Register interest with {info['name']} (190)", roi, add_months(roi, 2), "apply",
        f"{desc}. Status: {live_state.get('excerpt') or info['status']} State programs open and close; ROI does not guarantee nomination.",
        [task("Lodge EOI selecting 190 and this state", link=R.SKILLSELECT_URL), task("Lodge the state ROI when the program opens", link=info.get("graduateUrl") or info["url"]),
         task("Subscribe to the state's migration newsletter")], sources=[(info["name"] + " migration", info["url"]), R.SECONDARY["states"]], uncertain=True)
    nom = add_months(roi, 3)
    b.m("nominate", "State nomination and invitation", nom, add_months(nom, 3), "visa", "Lodge the 190 within 60 days of invitation. Nomination adds 5 points.", [task("Lodge the 190 application", link=R.VISA_URL["190"])], visa="190", uncertain=True)
    lo, hi = R.VISAS["190"]["processingMonths"]
    pr_lo, pr_hi = add_months(nom, 1 + lo), add_months(nom, 5 + hi)
    b.lane("BVA", add_months(nom, 1), pr_lo, "processing", "Bridging visa after lodging onshore")
    b.m("pr", "Permanent residence (190)", pr_lo, pr_hi, "pr", f"{R.VISAS['190']['processing']}. Then live and work in {info['name']} as committed (QLD: 2 years).", visa="190", uncertain=True)
    b.fee("190"); b.approx("medical", "Health examination"); b.approx("police", "Police certificates")
    pts = pts_now + 5
    reasons = []
    a = ctx.age()
    status_text = (live_state.get("excerpt") or info["status"]).lower()
    if a is not None and a >= 45:
        level = "Not available"; reasons.append("Age 45 or over rules out 190.")
    elif pts < R.PASS_MARK:
        level = "Stretch"; reasons.append(f"{pts} points with nomination is under the {R.PASS_MARK} pass mark today; experience and English can close this.")
    elif not ties and state not in {"SA", "TAS", "NT", "ACT", "WA"}:
        level = "Stretch"; reasons.append(f"No study or work ties recorded with {info['name']}.")
    else:
        level = "Viable"; reasons.append(f"{pts} points with the +5 nomination. {desc}.")
    if "closed" in status_text or "not yet open" in status_text:
        reasons.append(f"Program status: {live_state.get('excerpt') or info['status']}")
        if level == "Viable":
            level = "Viable"
    if cover_end and nom > cover_end:
        b.risks.append({"level": "high", "title": "Visa gap before nomination", "detail": f"Projected coverage ends {label(cover_end)} but nomination is estimated around {label(nom)}."})
    b.risks.append({"level": "medium", "title": "Program windows are unpredictable", "detail": "States allocate a fixed number of places each year and often close within weeks. Keep an EOI active for more than one route."})
    route = (["500", "485", "190"] if ctx.visa == "500" else [ctx.visa, "190"] if ctx.visa not in {"unknown"} else ["190"])
    return finalize(b, f"190-{state}", f"State nominated PR · {info['name']}", route,
                    f"Permanent visa through {info['name']} nomination. Rewards local work history more than a very high score.", level, reasons, (pr_lo, pr_hi),
                    dependencies=[f"{info['name']} program open with your occupation", desc, "Invitation after nomination"],
                    points={"now": pts_now, "withNomination": pts}, flexibility="Medium: 2 year state commitment (QLD)", obligation=f"Live and work in {info['name']} (QLD: 2 years after grant)", state=state)


def strat_491(ctx: Ctx, pts_now, state):
    b = Builder(ctx, f"s491{state.lower()}")
    info = R.STATES[state]
    grant485, cover_end = graduate_bridge(b)
    ready = prepare_basics(b)
    stream_ready, desc, ties = state_stream(ctx, state, "491")
    roi = max(ready, stream_ready)
    b.m("move", f"Move to regional {info['name']} and work there", max(ctx.today, ctx.work_start), stream_ready, "work",
        f"{info['regional']} {desc}.", [task(f"Search roles in regional {info['name']}", action=jobs_action(ctx, location="Toowoomba, QLD" if state == "QLD" else info["name"], note="Regional search")),
                                       task("Confirm the postcode is a designated regional area", link=R.REGIONAL_URL)],
        sources=[("Designated regional areas", R.REGIONAL_URL)])
    b.m("roi", f"Register interest for 491 with {info['name']}", roi, add_months(roi, 2), "apply", f"Regional nomination adds 15 points. {info['status']}",
        [task("Lodge EOI selecting 491 and this state", link=R.SKILLSELECT_URL), task("Lodge the ROI when open", link=info.get("graduateUrl") or info["url"])],
        sources=[(info["name"] + " migration", info["url"])], uncertain=True)
    inv = add_months(roi, 3)
    lo, hi = R.VISAS["491"]["processingMonths"]
    grant = add_months(inv, 1 + (lo + hi) / 2)
    b.m("grant491", "491 granted: 5 year regional provisional visa", grant, grant, "visa", "Condition 8579: live, work and study only in designated regional areas.",
        [task("Lodge within 60 days of invitation", link=R.VISA_URL["491"])], visa="491", uncertain=True)
    b.fee("491")
    b.lane("BVA", add_months(inv, 1), grant, "processing", "Bridging visa")
    b.lane("491", grant, add_months(grant, 60), "projected", "5 years; 191 eligible after 3")
    eligible191 = add_months(grant, 36)
    b.m("regional3", "3 years living and working regionally", grant, eligible191, "work", "Lodge a tax return every year. Keep address and employment evidence for the whole period.",
        [task("Lodge tax returns on time (3 notices of assessment needed)"), task("Keep a regional address history file")], visa="491")
    lo2, hi2 = R.VISAS["191"]["processingMonths"]
    pr_lo, pr_hi = add_months(eligible191, lo2), add_months(eligible191, hi2 + 3)
    b.m("pr", "Permanent residence (191)", pr_lo, pr_hi, "pr", R.VISAS["191"]["processing"], [task("Lodge the 191", link=R.VISA_URL["191"])], visa="191", uncertain=True)
    b.fee("191")
    level, reasons = "Viable", []
    a = ctx.age()
    if a is not None and a >= 45:
        level = "Not available"; reasons.append("Age 45 or over rules out 491.")
    elif ctx.regional == "no":
        level = "Not preferred"; reasons.append("You said you do not want to live regionally.")
    else:
        reasons.append(f"{pts_now + 15} points with the +15 regional nomination.")
        if ctx.regional != "yes":
            reasons.append("Confirm you can commit to 3+ years in a regional area.")
    if level == "Viable" and ctx.regional != "yes":
        level = "Stretch"
    b.risks.append({"level": "medium", "title": "Fewer 491 places in 2026-27", "detail": f"The national 491 planning level fell to {R.PLANNING_2026_27['491']:,} from {R.PLANNING_2026_27['previous']['491']:,}. Expect fewer nominations per state."})
    if state == "QLD":
        b.risks.append({"level": "medium", "title": "Locks out QLD 190 later", "detail": "Queensland will not nominate a current or past 491 applicant for 190."})
    route = (["500", "485", "491", "191"] if ctx.visa == "500" else [ctx.visa, "491", "191"])
    return finalize(b, f"491-{state}", f"Regional route · {info['name']} 491 to 191", route,
                    "Regional nomination adds 15 points, then permanent residence after 3 regional years.", level, reasons, (pr_lo, pr_hi),
                    dependencies=["Regional job and residence", f"{info['name']} 491 nomination", "3 compliant years"], points={"now": pts_now, "withNomination": pts_now + 15},
                    flexibility="Low: regional areas only for 3+ years", obligation="Designated regional area for at least 3 years", state=state)


def employer_ready(ctx: Ctx, years_needed: float):
    exp_now = ctx.au_exp + ctx.os_exp
    if exp_now >= years_needed:
        return ctx.today
    return add_months(max(ctx.today, ctx.work_start), (years_needed - exp_now) * 12)


def jobs_signal_text(ctx):
    js = ctx.live.get("jobs") or {}
    if not js.get("count"):
        return None
    return f"{js.get('sponsorship', 0)} of {js['count']} collected adverts for {js.get('role') or ctx.occupation} mention sponsorship; {js.get('citizenOrPr', 0)} ask for citizenship or PR; {js.get('clearance', 0)} mention a security clearance."


def strat_482(ctx: Ctx, pts_now):
    b = Builder(ctx, "s482")
    grant485, cover_end = graduate_bridge(b)
    if ctx.visa == "482":
        months = float(ctx.c.get("sponsorMonths") or 0)
        nominate = add_months(ctx.today, max(0, 24 - months))
        b.lane("482", ctx.today, ctx.visa_expiry or add_months(ctx.today, 24), "held", "Current visa")
        start482 = ctx.today
    else:
        ready = employer_ready(ctx, 1)
        start482 = max(ready, ctx.today)
        b.m("sponsor", "Find an employer willing to sponsor", ctx.today if ctx.employer == "yes" else max(ctx.today, ctx.work_start), start482, "work",
            f"Core Skills stream: occupation on the CSOL and salary at least ${R.CSIT:,} (from 1 July 2026) and the market rate. At least 1 year of relevant experience. " + (jobs_signal_text(ctx) or ""),
            [task("Target employers that already sponsor (larger engineering, defence-adjacent private firms, manufacturers)", action=jobs_action(ctx, note="Sponsor-friendly roles")),
             task("Ask early: sponsorship cost is mostly employer-paid (nomination $330, SAF levy, sponsorship $420)"), task("Negotiate a salary at or above CSIT and the market rate")],
            sources=[("Subclass 482", R.VISA_URL["482"]), R.SECONDARY["thresholds"]])
        lo, hi = R.VISAS["482"]["processingMonths"]
        grant = add_months(start482, (lo + hi) / 2)
        b.m("lodge482", "Employer nominates; you lodge the 482 (Core Skills)", start482, grant, "apply",
            "Your employer lodges sponsorship and nomination; you lodge the visa. Labour market testing (4 weeks of advertising) comes first for Core Skills.",
            [task("Employer completes labour market testing"), task("Lodge the 482 visa application", link=R.VISA_URL["482"]), task("Keep English evidence ready")],
            cost={"amount": ctx.fee("482")[0], "label": "482 visa charge"}, visa="482")
        b.fee("482")
        b.lane("482", grant, add_months(grant, 48), "projected", "Up to 4 years")
        nominate = add_months(grant, 24)
    b.m("trt2y", "Two years with an approved sponsor", start482, nominate, "work",
        "Since 29 November 2025 only time working for an approved sponsor counts. Changing employer needs a new nomination before you start; gaps without a sponsor do not count.",
        [task("Keep the same occupation and full-time hours"), task("If changing employer, get the new nomination approved first")], sources=[R.SECONDARY["trt"]])
    lo, hi = 4, 10
    pr_lo, pr_hi = add_months(nominate, lo), add_months(nominate, hi + 2)
    b.m("pr", "Employer nominates for 186 (Transition): permanent residence", nominate, pr_hi, "pr",
        f"Under 45 at application (exemptions exist), competent English, salary at least CSIT. Transition stream: {R.VISAS['186']['processing']}.",
        [task("Employer lodges the 186 nomination"), task("Lodge the 186 visa", link=R.VISA_URL["186"])], visa="186", uncertain=True)
    b.fee("186")
    level, reasons = "Viable", []
    a = ctx.age(nominate)
    if a is not None and a >= 45:
        level = "Stretch"; reasons.append(f"You would be {a} at 186 lodgement; only exempt cases can proceed.")
    if ctx.employer == "yes":
        level = "Strong" if level == "Viable" else level; reasons.append("You have an employer willing to sponsor.")
    else:
        level = "Depends on employer" if level == "Viable" else level; reasons.append("No sponsoring employer recorded yet.")
    reasons.append(f"Employer sponsored places rose to {R.PLANNING_2026_27['employer']:,} in 2026-27 (from {R.PLANNING_2026_27['previous']['employer']:,}).")
    if ctx.salary and ctx.salary < R.CSIT:
        b.risks.append({"level": "high", "title": "Salary under CSIT", "detail": f"${ctx.salary:,.0f} is under ${R.CSIT:,}. Core Skills nominations need at least CSIT and the market rate."})
    if cover_end and start482 > cover_end:
        b.risks.append({"level": "high", "title": "485 ends before you can be sponsored", "detail": f"Projected coverage ends {label(cover_end)}; 1 year of experience is reached around {label(start482)}."})
    b.risks.append({"level": "medium", "title": "Tied to your employer", "detail": "Losing the job starts a limited window to find a new sponsor or leave Australia; check the current period on Home Affairs."})
    route = (["500", "485", "482", "186"] if ctx.visa == "500" else ["482", "186"] if ctx.visa == "482" else [ctx.visa, "482", "186"])
    return finalize(b, "482-186", "Employer route · 482 to 186 Transition", route,
                    "Your employer sponsors a temporary 482, then nominates you for permanent residence after 2 years. Not points tested.", level, reasons, (pr_lo, pr_hi),
                    dependencies=["Sponsoring employer", f"Salary at least ${R.CSIT:,}", "Occupation on CSOL", "2 years with an approved sponsor"],
                    flexibility="Low to medium: tied to an approved sponsor", obligation="Work for the sponsor until PR")


def three_year_block(ctx: Ctx, ready: date, cover_end: date | None, what: str):
    """Routes needing 3 years of experience are unreachable if the current or graduate visa ends first."""
    if not cover_end or ready <= cover_end:
        return None
    exp_by_end = ctx.experience_at(cover_end)
    years = exp_by_end[0] + exp_by_end[1]
    via = "Your 485 gives up to 2 years (3 for research degrees), and time to find work comes out of that." if ctx.visa in {"500", "485"} else "Your current visa ends first."
    return (f"{what} needs 3 years of relevant experience before you apply. You would have about {years:.1f} years when your visa coverage ends ({label(cover_end)}). "
            f"{via} The realistic employer path is a 482 first, then 186 after 2 years with the sponsor.")


def strat_186de(ctx: Ctx, pts_now):
    b = Builder(ctx, "s186de")
    grant485, cover_end = graduate_bridge(b)
    ready = max(employer_ready(ctx, 3), prepare_basics(b, need_points_english=False))
    blocked = three_year_block(ctx, ready, cover_end, "186 Direct Entry")
    b.m("experience", "Build 3 years of post-qualification experience", max(ctx.today, ctx.work_start), ready, "work", "Direct Entry needs 3 years of relevant experience and a positive skills assessment.",
        [task("Keep skilled full-time work in the nominated occupation", action=jobs_action(ctx))])
    lo, hi = R.VISAS["186"]["processingMonths"]
    pr_lo, pr_hi = add_months(ready, 7), add_months(ready, 20)
    b.m("pr", "186 Direct Entry nomination and visa", ready, pr_hi, "pr", "Employer nominates at CSIT or above; Direct Entry processing 7 to 18 months.", [task("Lodge the 186 (Direct Entry)", link=R.VISA_URL["186"])], visa="186", uncertain=True)
    b.fee("186")
    level = "Depends on employer" if ctx.employer != "yes" else "Viable"
    reasons = [f"3 years of experience reached around {label(ready)}."]
    if blocked:
        level = "Not available"; reasons = [blocked]
    a = ctx.age(ready)
    if a is not None and a >= 45:
        level = "Not available"; reasons.append(f"Age {a} at lodgement.")
    route = (["500", "485", "186"] if ctx.visa == "500" else [ctx.visa, "186"])
    return finalize(b, "186-de", "Employer route · 186 Direct Entry", route, "Straight to permanent residence with an employer once you have 3 years of experience.",
                    level, reasons, (pr_lo, pr_hi), dependencies=["Sponsoring employer", "3 years experience", "Positive skills assessment"], flexibility="Medium", obligation="Genuine role with the nominating employer")


def strat_494(ctx: Ctx, pts_now):
    b = Builder(ctx, "s494")
    grant485, cover_end = graduate_bridge(b)
    ready = max(employer_ready(ctx, 3), prepare_basics(b, need_points_english=False))
    blocked = three_year_block(ctx, ready, cover_end, "The 494")
    b.m("experience", "3 years of full-time experience, then a regional sponsor", max(ctx.today, ctx.work_start), ready, "work", "Casual work does not count toward the 3 years.",
        [task("Search regional employers", action=jobs_action(ctx, location="Toowoomba, QLD", note="Regional employer search"))])
    lo, hi = R.VISAS["494"]["processingMonths"]
    grant = add_months(ready, (lo + hi) / 2)
    b.m("grant494", "494 granted: 5 years regional", ready, grant, "visa", f"Salary at least TSMIT ${R.TSMIT:,}.", [task("Lodge 494", link=R.VISA_URL["494"])], visa="494", uncertain=True)
    b.fee("494")
    b.lane("494", grant, add_months(grant, 60), "projected")
    e191 = add_months(grant, 36)
    pr_lo, pr_hi = add_months(e191, 3), add_months(e191, 12)
    b.m("pr", "Permanent residence (191)", e191, pr_hi, "pr", "After 3 years complying with the regional condition. You do not need to stay with the original employer for the 191.", visa="191", uncertain=True)
    b.fee("191")
    level = "Not preferred" if ctx.regional == "no" else "Depends on employer" if ctx.employer != "yes" else "Viable"
    reasons = ["You said you do not want to live regionally."] if ctx.regional == "no" else ["Needs a regional employer and 3 years of experience before applying."]
    if blocked and level != "Not preferred":
        level = "Not available"; reasons = [blocked.replace("a 482 first, then 186", "a 482 first (a regional employer can still sponsor it), then 186")]
    route = (["500", "485", "494", "191"] if ctx.visa == "500" else [ctx.visa, "494", "191"])
    return finalize(b, "494-191", "Regional employer · 494 to 191", route, "A regional employer sponsors you; permanent residence after 3 regional years.",
                    level, reasons, (pr_lo, pr_hi), dependencies=["Regional sponsoring employer", "3 years experience", "Skills assessment"], flexibility="Low", obligation="Regional area and sponsor")


def strat_partner(ctx: Ctx, pts_now):
    b = Builder(ctx, "spartner")
    rel = ctx.c.get("partnerRelationship")
    months = float(ctx.c.get("relationshipMonths") or 0)
    ready = ctx.today if rel in {"married", "registered"} or months >= 12 else add_months(ctx.today, 12 - months)
    if ready > ctx.today:
        b.m("relationship", "Meet the relationship requirement", ctx.today, ready, "prepare", "De facto relationships need 12 months of living together, unless registered in QLD, NSW, VIC, ACT, TAS or SA.",
            [task("Consider relationship registration (QLD Births, Deaths and Marriages)"), task("Build joint evidence: lease, bank accounts, bills")])
    b.m("lodge", "Lodge the partner visa (820/801) onshore", ready, add_months(ready, 1), "apply",
        "One application covers both stages. Bridging visa A usually allows work and study.",
        [task("Sponsor lodges sponsorship; you lodge the visa", link=R.VISA_URL["820"]), task("Statements, evidence across financial, household, social and commitment aspects"), task("Check your current visa has no 8503 condition", link=R.VEVO_URL)],
        cost={"amount": ctx.fee("820")[0], "label": "Partner visa charge"}, visa="820", sources=[R.SECONDARY["partner"]])
    b.fee("820")
    long_term = months >= 36
    g820 = add_months(ready, 17)
    b.lane("820", g820, add_months(ready, 24), "projected")
    pr_lo, pr_hi = (g820, add_months(ready, 24)) if long_term else (add_months(ready, 24), add_months(ready, 30))
    b.m("pr", "Permanent stage (801)", pr_lo, pr_hi, "pr", "Assessed about 2 years after lodgement; earlier for relationships of 3+ years.", visa="820", uncertain=True)
    level = "Strong" if ready <= ctx.today else "Viable"
    return finalize(b, "partner", "Partner route · 820 to 801", ["820", "801"] if ctx.visa not in {"500", "485"} else [ctx.visa, "820", "801"],
                    "Permanent residence through your relationship with an Australian citizen or permanent resident. Not points tested.", level,
                    [f"Relationship: {rel or 'not specified'}, {months:g} months."], (pr_lo, pr_hi), dependencies=["Genuine and continuing relationship", "Sponsor approval"], flexibility="High once granted", obligation="Relationship continues to the 801 decision")


def finalize(b: Builder, sid, name, route, summary, level, reasons, pr_window, dependencies=(), points=None, flexibility="", obligation="", state=None):
    b.milestones.sort(key=lambda m: (m["start"], m["end"]))
    gov = sum(c["amount"] for c in b.costs if c["kind"] == "government" and c.get("amount"))
    other_lo = sum(c["amount"] for c in b.costs if c["kind"] in {"assessment", "approx"} and c.get("amount"))
    other_hi = sum(c.get("amountHigh", c["amount"]) for c in b.costs if c["kind"] in {"assessment", "approx"} and c.get("amount"))
    rank = {"Strong": 0, "Viable": 1, "Depends on employer": 2, "Stretch": 3, "Needs evidence": 4, "Long shot": 5, "Not preferred": 6, "Not available": 7}
    pr_lo, pr_hi = pr_window
    track = "family" if sid.startswith("partner") else "sponsored" if sid.split("-")[0] in {"482", "186", "494"} else "independent"
    return {"id": sid, "track": track, "name": name, "route": [r for r in route if r and r not in {"unknown", "other"}], "summary": summary, "level": level, "rank": rank.get(level, 9),
            "reasons": reasons, "prWindow": {"from": iso(pr_lo), "to": iso(pr_hi), "label": f"{label(pr_lo)} to {label(pr_hi)}" if pr_lo else "Not estimable yet"},
            "monthsToPr": round(months_between(b.ctx.today, pr_lo)) if pr_lo else None,
            "costs": {"items": b.costs, "government": gov, "otherLow": round(other_lo), "otherHigh": round(other_hi)},
            "milestones": b.milestones, "lanes": b.lanes, "risks": b.risks, "dependencies": list(dependencies), "points": points,
            "flexibility": flexibility, "obligation": obligation, "state": state}


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------

def decision_tree(ctx: Ctx, pts_now, strategies):
    by = {s["id"].split("-")[0]: s for s in strategies}
    target, _ = ctx.target_189()
    def out(sid, lbl):
        s = next((x for x in strategies if x["id"] == sid or x["id"].startswith(sid)), None)
        return {"type": "outcome", "label": lbl, "strategy": s["id"] if s else None, "level": s["level"] if s else "Not available"}
    def q(qid, lbl, answer, yes, no, why=""):
        return {"type": "question", "id": qid, "label": lbl, "answer": answer, "why": why, "branches": [{"value": "yes", "label": "Yes", "child": yes}, {"value": "no", "label": "No", "child": no}]}
    yn = lambda v: None if v is None else ("yes" if v else "no")
    partner = None if not ctx.partner else ctx.partner == "partner_citizen_pr"
    employer = None if not ctx.employer else ctx.employer == "yes"
    exp3 = (ctx.au_exp + ctx.os_exp) >= 3
    competitive = None if target is None else pts_now >= target
    regional = None if ctx.regional in {"", "maybe"} else ctx.regional == "yes"
    state = ctx.states[0]
    tree = q("partner", "Is your partner an Australian citizen or permanent resident?", yn(partner),
             out("partner", "Partner visa 820 to 801"),
             q("employer", "Will an employer sponsor you?", yn(employer),
               q("exp3", "Do you already have 3+ years of relevant experience?", yn(exp3),
                 out("186-de", "186 Direct Entry"),
                 q("regionalEmployer", "Is the employer in a designated regional area?", yn(regional),
                   out("494-191", "494 then 191"), out("482-186", "482 then 186 Transition"))),
               q("points", f"Do your points meet the latest published 189 minimum{f' ({target})' if target else ''}?", yn(competitive),
                 out("189", "Skilled Independent 189"),
                 q("regional", "Will you live and work regionally for 3+ years?", yn(regional),
                   out(f"491-{state}", f"491 {state} then 191"),
                   q("state", f"Can you build {R.STATES[state]['name']} work history for state nomination?", "yes" if ctx.employed else None,
                     out(f"190-{state}", f"190 {state} nomination"), out("482-186", "Look for a sponsor (482 to 186)")))),
               why="Employer routes are not points tested."),
             why="Partner visas do not depend on occupation or points.")
    return tree


# ---------------------------------------------------------------------------
# Deadlines, inputs and assembly
# ---------------------------------------------------------------------------

def deadlines(ctx: Ctx, strategies):
    items = []
    def add(d, title, detail, severity="medium", kind="deadline"):
        if d and d >= ctx.today - timedelta(days=1):
            items.append({"date": iso(d), "title": title, "detail": detail, "severity": severity, "kind": kind, "daysAway": (d - ctx.today).days})
    if ctx.visa_expiry:
        add(ctx.visa_expiry, f"Current visa ({ctx.visa_text or ctx.visa}) expires", "Have a new application lodged or depart before this date. Check VEVO for the exact date and conditions.", "high")
    if ctx.visa == "500" and ctx.completion:
        add(ctx.completion, "Course completion", "Completion letter date starts the 6 month 485 window.", "medium", "milestone")
        d = add_months(ctx.completion, 6)
        if ctx.visa_expiry and ctx.visa_expiry < d:
            d = ctx.visa_expiry
        add(d, "Last day to lodge the 485", "Lodge in Australia, within 6 months of completion, while holding a visa.", "high")
    if ctx.dob:
        horizon = add_months(ctx.today, 96)
        for cliff, text, sev in ((25, "Age points rise from 25 to 30", "low"), (33, "Age points drop from 30 to 25", "medium"), (35, "485 age limit (under 35 when applying)", "high"),
                                 (40, "Age points drop from 25 to 15", "medium"), (45, "Points-tested and most employer PR visas need you under 45", "high")):
            day = birthday(ctx.dob, cliff)
            if cliff == 35 and ctx.visa != "500":
                continue
            if cliff != 45 and day > horizon:
                continue
            add(day, f"Turn {cliff}: {text}", "An invitation or application before this date locks in the earlier rule." if cliff != 25 else "Points improve from this date; an EOI update captures it.", sev)
    et = parse_date(ctx.c.get("englishTestDate"))
    if et:
        add(add_months(et, 12), "English result too old for a 485", "485 needs a test taken within 12 months before lodging.", "medium")
        add(add_months(et, 36), "English result expires for points", "Points-tested invitations need a test within 3 years.", "medium")
    sa = parse_date(ctx.c.get("skillsAssessmentDate"))
    if sa:
        add(add_months(sa, 36), "Skills assessment generally expires", "Most assessments are valid 3 years for points-tested visas unless the outcome says otherwise.", "medium")
    if ctx.visa in {"491", "494"} and parse_date(ctx.c.get("currentVisaGrantDate")):
        add(add_months(parse_date(ctx.c.get("currentVisaGrantDate")), 36), "Eligible to lodge 191", "Three years on the regional provisional visa.", "low", "milestone")
    items.sort(key=lambda x: x["date"])
    return items


def missing_inputs(ctx: Ctx):
    rows = []
    def need(field, lbl, why, weight):
        rows.append({"field": field, "label": lbl, "why": why, "weight": weight})
    if ctx.visa == "unknown": need("visa", "Current visa", "Every route starts from the visa you hold now.", 4)
    if not ctx.dob: need("dob", "Date of birth", "Age points, the 485 age limit and the under-45 cut-off all depend on it.", 3)
    if ctx.visa == "500" and not parse_date(ctx.c.get("courseCompletion")): need("courseCompletion", "Course completion date", "Starts the 485 clock and every graduate milestone.", 3)
    if not ctx.visa_expiry and ctx.visa not in SETTLED: need("visaExpiry", "Visa expiry", "Sets the coverage window and visa-gap warnings.", 3)
    if not ctx.english: need("englishLevel", "English level", "Worth 0 to 20 points and required for every route.", 2)
    if not ctx.assessment: need("skillsAssessment", "Skills assessment status", "Needed for 189, 190, 491, 494 and 186 Direct Entry.", 2)
    if not ctx.partner: need("partner", "Relationship status", "Up to 10 points, and unlocks the partner route.", 2)
    if not ctx.regional: need("regional", "Regional willingness", "Decides whether 491 and 494 routes fit.", 1)
    if not ctx.employer: need("employer", "Employer sponsorship", "Decides whether sponsored routes are shown.", 1)
    if not (ctx.c.get("employedInOccupation")): need("employedInOccupation", "Working in your occupation now?", "Experience points and state work requirements grow from your start date.", 1)
    return sorted(rows, key=lambda r: -r["weight"])


def build_plan(profile: dict, circumstances: dict, live: dict | None = None, today: date | None = None) -> dict:
    ctx = Ctx(profile, circumstances, live, today)
    pts = points_at(ctx)
    base = {"rulebook": {"version": R.RULEBOOK_VERSION, "verified": R.RULEBOOK_VERIFIED, "reformNote": R.POINTS_REFORM_NOTE, "stateStatusVerified": R.STATE_STATUS_VERIFIED,
                         "planning": R.PLANNING_2026_27, "thresholds": {"CSIT": R.CSIT, "SSIT": R.SSIT, "TSMIT": R.TSMIT},
                         "sources": [{"label": l, "url": u} for l, u in R.SECONDARY.values()] + [{"label": "Points table", "url": R.POINTS_TABLE_URL}, {"label": "Global processing times", "url": R.PROCESSING_URL}, {"label": "Visa pricing estimator", "url": R.PRICING_URL}, {"label": "Planning levels", "url": R.PLANNING_URL}]},
            "today": iso(ctx.today), "context": {"visa": ctx.visa, "visaText": ctx.visa_text, "visaExpiry": iso(ctx.visa_expiry), "daysOnVisa": (ctx.visa_expiry - ctx.today).days if ctx.visa_expiry else None,
                                                "age": ctx.age(), "occupation": ctx.occupation, "anzsco": ctx.anzsco, "family": ctx.family, "assessor": {"name": ctx.assessor["name"], "url": ctx.assessor["url"], "options": [{"label": o[0], "fee": o[1], "note": o[2]} for o in ctx.assessor["options"]]},
                                                "states": ctx.states, "completion": iso(ctx.completion), "workStart": iso(ctx.work_start), "qualification": ctx.qualification, "settled": ctx.visa in SETTLED, "employer": ctx.employer, "pyEligible": bool(ctx.assessor.get("professionalYear")),
                                                "field": ctx.field, "fields": [{"value": v, "label": l, "assessor": R.ASSESSORS[k]["name"]} for v, l, k in R.FIELDS_OF_STUDY]},
            "points": pts, "pointsOptions": points_options(ctx), "pointsTimeline": points_timeline(ctx), "assumptions": ctx.assumptions, "missing": missing_inputs(ctx)}
    if ctx.visa in SETTLED:
        base.update(strategies=[], tree={"type": "outcome", "label": "You already hold permanent residence or citizenship", "level": "Strong"}, visas=[], deadlines=deadlines(ctx, []),
                    headline={"title": "No migration pathway needed", "detail": "Your selected status is permanent. Pathway focuses on career progression instead."})
        return base
    strategies = []
    if ctx.partner == "partner_citizen_pr":
        strategies.append(strat_partner(ctx, pts["total"]))
    strategies.append(strat_189(ctx, pts["total"]))
    for st in ctx.states[:2]:
        strategies.append(strat_190(ctx, pts["total"], st))
    strategies.append(strat_491(ctx, pts["total"], ctx.states[0]))
    ruled_out = []
    if ctx.employer == "no":
        ruled_out.append({"id": "sponsored", "name": "Employer sponsored routes (482 to 186, 494 to 191, 186 Direct Entry)", "track": "sponsored",
                          "reason": "Hidden because you answered No to employer sponsorship. Change that answer to compare them."})
    else:
        strategies.append(strat_482(ctx, pts["total"]))
        if ctx.visa != "482":
            strategies.append(strat_186de(ctx, pts["total"]))
            strategies.append(strat_494(ctx, pts["total"]))
    for s_ in [x for x in strategies if x["level"] in {"Not available", "Not preferred"}]:
        ruled_out.append({"id": s_["id"], "name": s_["name"], "track": s_["track"], "route": s_["route"], "reason": " ".join(s_["reasons"][:1])})
    strategies = [x for x in strategies if x["level"] not in {"Not available", "Not preferred"}]
    strategies.sort(key=lambda s: (s["rank"], s["monthsToPr"] if s["monthsToPr"] is not None else 999))
    codes = ["485"] if ctx.visa in {"500", "485"} else []
    codes += ["189", "190", "491", "482", "186", "494", "191"] + (["820"] if ctx.partner == "partner_citizen_pr" else []) 
    visas = []
    for code in codes:
        v = R.VISAS[code]
        amount, basis, live_fee = ctx.fee(code)
        checks = visa_checks(ctx, code, pts["total"])
        counts = {k: sum(1 for c in checks if c["state"] == k) for k in ("met", "unmet", "unknown", "later")}
        visas.append({"code": code, "name": v["name"], "kind": v["kind"], "stage": v["stage"], "fee": amount, "feeBasis": basis, "feeCheckedAt": (live_fee or {}).get("checkedAt"), "feeNote": v.get("feeNote"),
                      "processing": v["processing"], "stay": v["stay"], "rights": v["rights"], "keyConditions": v["keyConditions"], "notes": v["notes"], "url": R.VISA_URL.get(code),
                      "checks": checks, "counts": counts, "status": "blocked" if counts["unmet"] and any(c["id"] in {"age", "previous", "record", "sponsor"} and c["state"] == "unmet" for c in checks) else "ready" if not counts["unmet"] and not counts["unknown"] and not counts["later"] else "work" if counts["unmet"] or counts["later"] else "check"})
    best = strategies[0] if strategies else None
    tracks = {}
    for t in ("independent", "sponsored", "family"):
        best_t = next((x for x in strategies if x["track"] == t), None)
        if best_t:
            tracks[t] = best_t["id"]
    base.update(strategies=strategies, ruledOut=ruled_out, tracks=tracks, visas=visas, tree=decision_tree(ctx, pts["total"], strategies), deadlines=deadlines(ctx, strategies),
                headline={"title": best["name"] if best else "No route estimated", "detail": "; ".join(best["reasons"][:2]) if best else "", "prWindow": best["prWindow"] if best else None},
                states=[{"code": code, "name": info["name"], "status": ((live or {}).get("states") or {}).get(code, {}).get("excerpt") or info["status"],
                         "statusCheckedAt": ((live or {}).get("states") or {}).get(code, {}).get("checkedAt"), "statusBasis": "live" if ((live or {}).get("states") or {}).get(code) else "rulebook",
                         "url": info["url"], "streams": info["streams"], "regional": info["regional"],
                         "shortage": (((live or {}).get("shortage") or {}).get("stateRatings") or {}).get(code)} for code, info in R.STATES.items()],
                jobs=(live or {}).get("jobs"), round=ctx.round() or None)
    return base
