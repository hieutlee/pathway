"""Advert evidence and personal comparisons. No model generated market claims."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from urllib.parse import urlsplit, urlunsplit

from intelligence import clean, norm
from job_provider import normalize_job, token_match
from skill_reasoning import assess, eligibility

LEVELS = ("Junior", "Mid level", "Senior", "Leadership", "Unspecified")
# A deliberately visible starter vocabulary. Counts mean mentions, not mandatory skills.
SKILLS = {
    "Python": ["python"], "C++": ["c++"], "C#": ["c#"], "Java": ["java"],
    "JavaScript": ["javascript"], "TypeScript": ["typescript"], "SQL": ["sql"],
    "React": ["react"], "AWS": ["aws", "amazon web services"], "Azure": ["azure"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes"], "Git": ["git"],
    "PLC": ["plc", "plcs", "programmable logic controller"], "SCADA": ["scada"],
    "HMI": ["hmi"], "Siemens TIA Portal": ["tia portal"], "Allen Bradley": ["allen bradley", "allen-bradley"],
    "Control systems": ["control systems", "control system", "control theory"],
    "Embedded systems": ["embedded systems", "embedded software", "embedded firmware"],
    "ROS": ["ros", "ros2", "robot operating system"], "Robotics": ["robotics", "robotic"],
    "CAD": ["cad", "computer aided design", "computer-aided design"],
    "SolidWorks": ["solidworks"], "AutoCAD": ["autocad"], "MATLAB": ["matlab"],
    "Simulink": ["simulink"], "Altium": ["altium"], "PCB design": ["pcb design"],
    "Troubleshooting": ["troubleshooting", "fault finding"],
    "Functional safety": ["functional safety", "iec 61508", "iso 13849"],
    "Machine vision": ["machine vision", "computer vision"],
    "Machine learning": ["machine learning", "deep learning"],
    "AI tools": ["generative ai", "artificial intelligence", "chatgpt", "copilot", "ai tools", "ai-assisted"],
    "Excel": ["excel"], "Power BI": ["power bi"], "Tableau": ["tableau"],
    "Project management": ["project management"], "Stakeholder management": ["stakeholder management"],
    "Communication": ["communication skills", "written communication", "verbal communication"],
    "Customer service": ["customer service"], "Salesforce": ["salesforce"], "SAP": ["sap"],
    "Xero": ["xero"], "MYOB": ["myob"], "Revit": ["revit"], "BIM": ["bim"],
    "AHPRA registration": ["ahpra"], "Patient care": ["patient care"],
    "Clinical assessment": ["clinical assessment"], "Teaching": ["teaching"],
    "Risk assessment": ["risk assessment"], "Quality assurance": ["quality assurance"],
    "Instrumentation": ["instrumentation", "instruments", "sensors and transmitters"], "Electrical design": ["electrical design", "single line diagram", "schematic design"],
    "Modbus": ["modbus"], "Ignition": ["ignition scada", "inductive automation"], "Linux": ["linux"], "CUDA": ["cuda"], "RTOS": ["rtos", "freertos"],
    "Agile": ["agile", "scrum"], "Testing": ["software testing", "unit testing", "test automation", "testing and commissioning", "verification and validation", "integration testing", "system testing"], "Documentation": ["technical documentation", "documentation"],
    "Problem solving": ["problem solving", "problem-solving"], "Teamwork": ["teamwork", "team player", "collaborat"], "Data analysis": ["data analysis", "data analytics"],
    "Commissioning": ["commissioning"], "Electrical licence": ["electrical licence", "a-grade", "restricted electrical licence"], "Driver licence": ["driver's licence", "drivers licence", "driver licence"],
}


# Work-rights language in adverts. Evidence is quoted; nothing is inferred from silence.
WORK_RIGHTS = [
    ("citizen_pr", "Citizens or PR only", r"(?:must|need to|required to|you will) (?:be|hold) (?:an? )?(?:australian )?(?:citizen|permanent resident)|australian citizen(?:ship)?(?: is)? (?:required|essential|mandatory)|citizens? (?:or|and|/) permanent residents? only|(?:only|exclusively) (?:open|available) to (?:australian )?citizens|(?:australian )?citizenship (?:is )?(?:required|essential|mandatory)|permanent residency (?:is )?(?:required|essential)|must be an australian citizen|australian citizens? (?:or|and|/) permanent residents?"),
    ("clearance", "Security clearance", r"security clearance|baseline (?:security )?clearance|\bnv1\b|\bnv2\b|\bagsva\b|negative vetting|ability to (?:obtain|gain|hold) (?:and maintain )?(?:a |an )?(?:australian )?(?:government )?(?:security )?clearance"),
    ("no_sponsorship", "No sponsorship", r"(?:no|not|unable to|cannot|can't|do not|does not|will not) (?:offer |provide |consider )?(?:visa )?sponsor(?:ship)?|sponsorship (?:is )?not (?:available|offered|provided)"),
    ("sponsorship", "Sponsorship mentioned", r"visa sponsorship (?:is |may be )?(?:available|offered|provided|considered)|(?:will|can|happy to|open to|able to) sponsor|sponsorship (?:is |may be )?(?:available|offered|considered)|(?:482|tss|skills in demand|sid) (?:visa )?sponsorship"),
    ("work_rights", "Work rights required", r"(?:full|unrestricted|valid|current|existing) (?:australian )?(?:working|work) rights|right to work in australia|(?:legally )?(?:eligible|entitled) to work in australia|working rights in australia"),
]


def work_rights(text):
    for key, label, pattern in WORK_RIGHTS:
        match = re.search(pattern, text or "", re.I)
        if match:
            return {"category": key, "label": label, "evidence": excerpt(text, *match.span(), radius=80)}
    return {"category": "not_stated", "label": "Not stated", "evidence": ""}


def excerpt(text, start, end, radius=95):
    return ("…" if start > radius else "") + text[max(0, start-radius):min(len(text), end+radius)].strip() + ("…" if end+radius < len(text) else "")


def mentions(text, vocabulary=SKILLS):
    result = []
    for label, aliases in vocabulary.items():
        for alias in aliases:
            match = re.search(r"(?<![a-z0-9])"+re.escape(alias)+r"(?![a-z0-9])", text, re.I)
            if match:
                result.append({"skill": label, "evidence": excerpt(text, *match.span())})
                break
    return result


def experience_requirement(text):
    # Only an explicit requirement, not company history or a preferred qualification.
    pattern = r"(?P<lo>\d{1,2})(?:\s*[-–to]+\s*(?P<hi>\d{1,2}))?\s*\+?\s*years?[’']?\s+(?:of\s+)?(?:(?:relevant|professional|commercial|industry|practical|hands.on)\s+)?experience"
    hits = []
    for match in re.finditer(pattern, text, re.I):
        left = max(text.rfind(".", 0, match.start()), text.rfind(";", 0, match.start()), text.rfind("\n", 0, match.start()))+1
        right = text.find(".", match.end())
        sentence = text[left:right if right >= 0 else len(text)][:500]
        if re.search(r"preferred|desirable|ideally|advantage|nice to have", sentence, re.I):
            continue
        if not re.search(r"require|minimum|at least|must|you (?:have|bring)|you will have|you'll have|candidate|applicant|seeking|looking for", sentence, re.I):
            continue
        years = int(match["lo"])
        if years <= 30:
            hits.append({"minimum": years, "maximum": int(match["hi"]) if match["hi"] else None, "evidence": excerpt(text, *match.span())})
    # Minimum per individual tool is not total career experience. Keep the evidence visible.
    return max(hits, key=lambda x: x["minimum"]) if hits else None


def seniority(title, provider_level, requirement):
    for level, pattern in (
        ("Leadership", r"\b(?:director|head of|vice president|chief|engineering manager|general manager)\b"),
        ("Senior", r"\b(?:senior|sr\.?|principal|staff engineer|technical lead|team lead|lead engineer|lead developer)\b"),
        ("Junior", r"\b(?:junior|jr\.?|graduate|entry.level|intern|trainee|apprentice)\b"),
        ("Mid level", r"\b(?:mid.level|intermediate)\b"),
    ):
        if re.search(pattern, title, re.I):
            return {"level": level, "basis": "Advert title", "evidence": title}
    exact = {"internship": "Junior", "entry level": "Junior", "entry-level": "Junior", "junior": "Junior", "senior": "Senior", "mid level": "Mid level", "mid-level": "Mid level", "director": "Leadership", "executive": "Leadership"}
    if provider_level.lower() in exact:
        return {"level": exact[provider_level.lower()], "basis": "Provider label", "evidence": provider_level}
    if requirement:
        years = requirement["minimum"]
        level = "Junior" if years <= 2 else "Mid level" if years <= 5 else "Senior"
        return {"level": level, "basis": "Inferred from stated experience", "evidence": requirement["evidence"]}
    # LinkedIn's Mid-Senior and Associate labels do not resolve the requested buckets.
    return {"level": "Unspecified", "basis": "Not resolved", "evidence": provider_level or "No explicit level or experience requirement detected."}


def salary_evidence(text):
    if not text:
        return None
    # Require a currency marker; preserve pay periods and super instead of annualising.
    amount = r"(?P<a>\d[\d,]*(?:\.\d+)?)\s*(?P<ak>[kK])?"
    match = re.search(r"(?P<currency>AUD|USD|NZD|AU\$|A\$|US\$|NZ\$|\$)\s*"+amount+r"(?:\s*(?:-|–|to)\s*(?:AUD|USD|NZD|AU\$|A\$|US\$|NZ\$|\$)?\s*(?P<b>\d[\d,]*(?:\.\d+)?)\s*(?P<bk>[kK])?)?", text, re.I)
    if not match:
        return None
    context = text[max(0, match.start()-35):match.end()+100]
    # Reject ambiguous multiple amounts such as base + bonus rather than summing them.
    if re.search(r"\b(?:bonus|commission)\b", context, re.I) and not re.search(r"\b(?:base|salary|pay)\b", context, re.I):
        return None
    period = next((p for p, regex in (
        ("year", r"per\s*(?:annum|year)|/(?:year|yr|annum)|\bp\.?a\.?\b|annual|yearly"),
        ("hour", r"per\s*hour|/(?:hour|hr)|hourly|\bph\b"),
        ("day", r"per\s*day|/day|daily"), ("week", r"per\s*week|/week|weekly"),
        ("month", r"per\s*month|/month|monthly")) if re.search(regex, context, re.I)), None)
    if not period:
        return None
    low = float(match["a"].replace(",", "")) * (1000 if match["ak"] or (match["bk"] and len(match["a"])<=3) else 1)
    high = float(match["b"].replace(",", "")) * (1000 if match["bk"] else 1) if match["b"] else low
    if low <= 0 or high < low:
        return None
    currency_raw = match["currency"].upper()
    currency = "USD" if currency_raw.startswith("US") else "NZD" if currency_raw.startswith("NZ") else "AUD" if currency_raw != "$" else "$ (currency unstated)"
    basis = "Includes super" if re.search(r"incl(?:udes|uding|usive|\.)?.{0,12}super", context, re.I) else "Excludes super" if re.search(r"(?:\+|plus|excl(?:udes|uding|usive|\.)?).{0,12}super", context, re.I) else "Package" if re.search(r"package|total remuneration", context, re.I) else "Super / package unspecified"
    return {"min": low, "max": high, "currency": currency, "period": period, "basis": basis, "evidence": context.strip()}


def canonical_job_key(job):
    parsed = urlsplit(job["url"])
    if parsed.hostname and (parsed.hostname == "linkedin.com" or parsed.hostname.endswith(".linkedin.com")):
        found = re.search(r"(?:/view/(?:[^/]*-)?|currentJobId=)(\d{6,})", job["url"])
        if found:
            return "linkedin:"+found[1]
    # Keep non-tracking queries: many job boards identify a job with ?id=.
    from urllib.parse import parse_qsl, urlencode
    query = urlencode(sorted((k,v) for k,v in parse_qsl(parsed.query) if not k.startswith("utm_") and k not in {"trk", "trackingId", "refId"}))
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), query, ""))


def corpus_jobs(items):
    jobs, seen = [], set()
    for raw in items:
        job = normalize_job(raw)
        if not job:
            continue
        key = canonical_job_key(job)
        if key in seen:
            continue
        seen.add(key)
        job["id"] = key
        job["experienceRequirement"] = experience_requirement(job["description"])
        job["seniority"] = seniority(job["title"], clean(raw.get("seniorityLevel") or ""), job["experienceRequirement"])
        job["skillMentions"] = mentions(job["description"])
        job["workRights"] = work_rights(job["description"])
        salary_text = job["salary"]
        if not salary_text:
            # Only description excerpts explicitly about salary, pay or remuneration.
            match = re.search(r"(?:salary|remuneration|pay range|pay rate|hourly rate)[^.;\n]{0,160}", job["description"], re.I)
            salary_text = match[0] if match else ""
        job["salaryEvidence"] = salary_evidence(salary_text)
        if not job["salary"] and job["salaryEvidence"]:
            job["salary"] = salary_text
        jobs.append(job)
    return jobs


def market_summary(jobs):
    counts = Counter(j["seniority"]["level"] for j in jobs)
    companies = Counter(j["company"] for j in jobs if j["company"])
    skills = Counter(s["skill"] for j in jobs for s in j["skillMentions"])
    skill_examples = {}
    for j in jobs:
        for m in j["skillMentions"]:
            skill_examples.setdefault(m["skill"], [])
            if len(skill_examples[m["skill"]]) < 3:
                skill_examples[m["skill"]].append({"title": j["title"], "company": j["company"], "url": j["url"], "evidence": m["evidence"]})
    salary_groups = defaultdict(list)
    for job in jobs:
        salary = job["salaryEvidence"]
        if salary:
            salary_groups[(salary["currency"], salary["period"], salary["basis"])].append(salary)
    salaries = [{"currency": k[0], "period": k[1], "basis": k[2], "count": len(v), "min": min(s["min"] for s in v), "max": max(s["max"] for s in v)} for k,v in sorted(salary_groups.items())]
    junior_demand = [j for j in jobs if j["seniority"]["level"]=="Junior" and j["experienceRequirement"] and j["experienceRequirement"]["minimum"]>=3]
    ai_jobs = [j for j in jobs if any(s["skill"] in {"AI tools", "Machine learning"} for s in j["skillMentions"])]
    rights = Counter(j.get("workRights", {}).get("category", "not_stated") for j in jobs)
    def evidence(jobs):
        return [{"title": j["title"], "url": j["url"], "evidence": j["experienceRequirement"]["evidence"]} for j in jobs[:4]]
    return {
        "count": len(jobs), "levels": [{"level": level, "count": counts[level]} for level in LEVELS],
        "companies": [{"name": name, "count": count} for name,count in companies.most_common(12)],
        "companyCount": len(companies), "unknownCompanyCount": sum(not j["company"] for j in jobs),
        "skills": [{"skill": skill, "count": count, "examples": skill_examples.get(skill, [])} for skill,count in skills.most_common(14)],
        "describedCount": sum(bool(j["description"]) for j in jobs),
        "salaryDisclosedCount": sum(bool(j["salary"]) for j in jobs), "salaries": salaries,
        "experienceExamples": [{"title": j["title"], "url": j["url"], **j["experienceRequirement"]} for j in jobs if j["experienceRequirement"]][:5],
        "juniorDemand": {"count": len(junior_demand), "totalJunior": counts["Junior"], "examples": evidence(junior_demand)},
        "workRights": {"counts": {key: rights[key] for key, _, _ in WORK_RIGHTS} | {"not_stated": rights["not_stated"]},
                       "examples": [{"title": j["title"], "url": j["url"], "category": j["workRights"]["category"], "label": j["workRights"]["label"], "evidence": j["workRights"]["evidence"]} for j in jobs if j.get("workRights", {}).get("category") not in (None, "not_stated")][:8]},
        "aiMentions": {"count": len(ai_jobs), "examples": [{"title": j["title"], "url": j["url"], "evidence": next(s["evidence"] for s in j["skillMentions"] if s["skill"] in {"AI tools", "Machine learning"})} for j in ai_jobs[:4]]},
    }


def profile_evidence(profile):
    """Candidate evidence for reasoning: listed skills plus resume entries, each with its source."""
    items = []
    # Work, projects and study first so reasons cite real experience before the skills list.
    for e in profile.get("evidence", []) or []:
        if isinstance(e, dict) and e.get("text"):
            items.append({"source": clean(e.get("source") or "Your resume")[:120], "text": clean(e["text"])[:2500]})
    supplied = [clean(x) for x in profile.get("skills", []) if isinstance(x, str) and x.strip()]
    if supplied:
        items.append({"source": "Your skills list", "text": " | ".join(supplied)})
    return items


def personal_fit(job, profile, role, evidence=None, cache=None):
    evidence = evidence if evidence is not None else profile_evidence(profile)
    cache = cache if cache is not None else {}
    advertised = list(dict.fromkeys(s["skill"] for s in job["skillMentions"]))
    statuses = []
    for skill in advertised:
        if skill not in cache:
            cache[skill] = assess(skill, evidence, SKILLS.get(skill, []))
        st = dict(cache[skill])
        st["advertEvidence"] = next((m["evidence"] for m in job["skillMentions"] if m["skill"] == skill), "")
        statuses.append(st)
    have = [s for s in statuses if s["status"] == "have"]
    transferable = [s for s in statuses if s["status"] == "transferable"]
    gaps = [s for s in statuses if s["status"] == "gap"]
    years = profile.get("experienceYears")
    years = float(years) if isinstance(years, (int, float)) and not isinstance(years, bool) and years >= 0 else None
    required = job["experienceRequirement"]
    years_gap = max(0, required["minimum"]-years) if required and years is not None else None
    target_role = role or profile.get("occupation") or ""
    title_tokens = [w for w in re.findall(r"[a-z0-9]+", norm(target_role)) if w not in {"senior", "junior", "mid", "level", "graduate", "a", "an", "the", "and", "or"}]
    title_matches = bool(title_tokens) and all(token_match(w, job["title"]) for w in title_tokens)
    coverage = (len(have) + 0.7 * len(transferable)) / len(statuses) if statuses else None
    elig = eligibility(job.get("workRights"), profile.get("visa", ""))
    if not job["description"] or coverage is None:
        label = "Needs review"
    elif years_gap or (job["seniority"]["level"] in {"Senior", "Leadership"} and years is not None and years < 5):
        label = "Stretch"
    elif coverage >= 0.7 and (not required or (years is not None and not years_gap)):
        label = "Strong match" if (title_matches or coverage >= 0.85) else "Good match"
    elif coverage >= 0.4:
        label = "Good match"
    else:
        label = "Stretch"
    reasons = []
    if statuses:
        reasons.append(f"{len(have)} of {len(statuses)} advertised skills are on your resume" + (f", {len(transferable)} more are transferable" if transferable else "") + ".")
    if required:
        reasons.append(f"Asks for {required['minimum']}+ years; your profile shows {years:g}." if years is not None else f"Asks for {required['minimum']}+ years of experience.")
    if not title_matches and target_role:
        reasons.append("The title differs from your search. Check the duties.")
    return {"label": label, "eligibility": elig, "skills": statuses, "haveCount": len(have), "transferableCount": len(transferable), "gapCount": len(gaps),
            "coverage": round(coverage, 2) if coverage is not None else None,
            "supportedSkills": [s["skill"] for s in have + transferable], "notEvidencedSkills": [s["skill"] for s in gaps],
            "experienceGap": years_gap, "titleMatches": title_matches, "reasons": reasons,
            "explanation": "Skills are compared with your own resume: green means it appears there, light green means related work that transfers, grey means no evidence yet. Work-rights notes come from the advert's own wording."}


FIT_ORDER = {"Strong match": 0, "Good match": 1, "Stretch": 2, "Needs review": 3}


def analyse(items, profile, role):
    jobs = corpus_jobs(items)
    market = {"all": market_summary(jobs), "byLevel": {level: market_summary([j for j in jobs if j["seniority"]["level"]==level]) for level in LEVELS}}
    evidence, cache = profile_evidence(profile), {}
    results = []
    for job in jobs:
        fit = personal_fit(job, profile, role, evidence, cache)
        results.append({**{k:v for k,v in job.items() if k!="description"}, "fit": fit,
                        "reason": " ".join(fit["reasons"]), "matchedSkills": fit["supportedSkills"]})
    results.sort(key=lambda j: (j["fit"]["eligibility"]["tier"], FIT_ORDER[j["fit"]["label"]], -(j["fit"]["coverage"] or 0), not j["fit"]["titleMatches"], j["title"]))
    advertised = {s["skill"] for j in jobs for s in j["skillMentions"]}
    skill_status = {}
    for skill in advertised:
        skill_status[skill] = cache.get(skill) or assess(skill, evidence, SKILLS.get(skill, []))
    return {"roles": results, "count": len(results), "market": market, "skillStatus": skill_status,
            "matchingMethod": "Your resume evidence is compared with each advert's own wording. Direct mentions, transferable related work and gaps are shown with their sources. No hiring probability is estimated."}
