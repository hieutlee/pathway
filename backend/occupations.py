"""Occupation catalogue: plain-language occupations mapped to the ANZSCO codes used for migration.

People should never need to know a code. They pick an occupation they recognise; Pathway carries
the code behind the scenes for the shortage list, invitation rounds and the assessing authority.
Codes are the commonly used migration codes and must be confirmed with the assessing authority.
"""
from __future__ import annotations

import re

# title, ANZSCO code, official ANZSCO title, field (assessor family), job search title, keywords
CATALOGUE = [
    ("Mechatronics Engineer", "233999", "Engineering Professionals nec", "engineering", "Mechatronics Engineer", ["mechatronic", "robotics", "automation", "control systems", "plc", "hmi", "embedded", "motor control", "scada"]),
    ("Robotics Engineer", "233999", "Engineering Professionals nec", "engineering", "Robotics Engineer", ["robot", "robotics", "ros", "kinematics", "autonomous"]),
    ("Automation and Controls Engineer", "233311", "Electrical Engineer", "engineering", "Controls Engineer", ["plc", "scada", "hmi", "tia portal", "studio 5000", "control logic", "industrial automation", "commissioning", "pid"]),
    ("Mechanical Engineer", "233512", "Mechanical Engineer", "engineering", "Mechanical Engineer", ["mechanical", "solidworks", "cad", "fea", "thermodynamics", "hvac", "manufacturing", "dfm"]),
    ("Electrical Engineer", "233311", "Electrical Engineer", "engineering", "Electrical Engineer", ["electrical", "power systems", "switchboard", "high voltage", "protection", "power distribution"]),
    ("Electronics Engineer", "233411", "Electronics Engineer", "engineering", "Electronics Engineer", ["electronics", "pcb", "circuit", "firmware", "microcontroller", "embedded", "altium"]),
    ("Embedded Software Engineer", "233411", "Electronics Engineer", "engineering", "Embedded Software Engineer", ["embedded", "firmware", "rtos", "freertos", "arm cortex", "microcontroller", "spi", "i2c", "uart", "can"]),
    ("Civil Engineer", "233211", "Civil Engineer", "engineering", "Civil Engineer", ["civil", "infrastructure", "roads", "drainage", "geotechnical", "12d"]),
    ("Structural Engineer", "233214", "Structural Engineer", "engineering", "Structural Engineer", ["structural", "steel design", "concrete design", "spacegass", "etabs"]),
    ("Chemical Engineer", "233111", "Chemical Engineer", "engineering", "Chemical Engineer", ["chemical", "process engineering", "reactor", "aspen", "process plant"]),
    ("Industrial Engineer", "233511", "Industrial Engineer", "engineering", "Industrial Engineer", ["industrial engineering", "lean", "six sigma", "process improvement", "operations research"]),
    ("Production or Plant Engineer", "233513", "Production or Plant Engineer", "engineering", "Production Engineer", ["production", "plant", "manufacturing", "maintenance", "reliability"]),
    ("Software Engineer", "261313", "Software Engineer", "ict", "Software Engineer", ["software", "c++", "java", "algorithms", "unit testing", "ci/cd", "object-oriented", "cuda", "kernel"]),
    ("Developer Programmer", "261312", "Developer Programmer", "ict", "Software Developer", ["developer", "javascript", "typescript", "react", "node", "api", "web"]),
    ("Data Scientist", "224115", "Data Scientist", "ict", "Data Scientist", ["data science", "machine learning", "pytorch", "tensorflow", "statistics", "model"]),
    ("Data Analyst", "224114", "Data Analyst", "ict", "Data Analyst", ["data analyst", "power bi", "tableau", "sql", "dashboard", "reporting", "excel"]),
    ("ICT Business Analyst", "261111", "ICT Business Analyst", "ict", "Business Analyst", ["business analyst", "requirements", "stakeholder", "user stories", "process mapping"]),
    ("Cyber Security Engineer", "261315", "Cyber Security Engineer", "ict", "Cyber Security Engineer", ["cyber", "security", "siem", "penetration", "soc", "iso 27001"]),
    ("Network Engineer", "263111", "Computer Network and Systems Engineer", "ict", "Network Engineer", ["network", "cisco", "routing", "switching", "firewall", "ccna"]),
    ("Accountant", "221111", "Accountant (General)", "accounting", "Graduate Accountant", ["accountant", "accounting", "xero", "myob", "reconciliation", "financial statements", "tax"]),
    ("Management Accountant", "221112", "Management Accountant", "accounting", "Management Accountant", ["management accounting", "budget", "forecast", "variance", "cost"]),
    ("External Auditor", "221213", "External Auditor", "accounting", "Graduate Auditor", ["audit", "auditor", "assurance"]),
    ("Registered Nurse", "254499", "Registered Nurses nec", "nursing", "Registered Nurse", ["nurse", "nursing", "patient", "clinical", "ahpra", "ward"]),
    ("Secondary School Teacher", "241411", "Secondary School Teacher", "teaching", "Secondary Teacher", ["teacher", "teaching", "secondary school", "curriculum", "classroom"]),
    ("Early Childhood Teacher", "241111", "Early Childhood (Pre-primary School) Teacher", "teaching", "Early Childhood Teacher", ["early childhood", "kindergarten", "childcare"]),
    ("Marketing Specialist", "225113", "Marketing Specialist", "other", "Marketing Coordinator", ["marketing", "campaign", "seo", "brand", "social media", "google analytics"]),
    ("Management Consultant", "224711", "Management Consultant", "other", "Graduate Consultant", ["consulting", "consultant", "strategy", "operations improvement"]),
    ("Construction Project Manager", "133111", "Construction Project Manager", "other", "Project Manager Construction", ["construction", "site", "project manager", "contracts"]),
    ("Quantity Surveyor", "233213", "Quantity Surveyor", "other", "Quantity Surveyor", ["quantity surveyor", "cost estimation", "bill of quantities"]),
    ("Architect", "232111", "Architect", "other", "Graduate Architect", ["architect", "architecture", "revit", "archicad"]),
    ("Social Worker", "272511", "Social Worker", "other", "Social Worker", ["social work", "case management", "community services"]),
    ("Physiotherapist", "252511", "Physiotherapist", "other", "Physiotherapist", ["physiotherapy", "physiotherapist", "rehabilitation"]),
]


def by_title(title: str):
    t = (title or "").strip().lower()
    return next((o for o in CATALOGUE if o[0].lower() == t), None)


FIELD_WORDS = {"engineering": ["engineer", "engineering"], "ict": ["developer", "software", "data", "analyst", "programmer", "ict", "it "],
               "accounting": ["account", "audit", "finance", "tax"], "nursing": ["nurse", "nursing", "clinical"], "teaching": ["teacher", "teaching", "tutor"],
               "trades": ["apprentice", "technician", "tradesperson"], "other": []}


def entry(o, score=0, reasons=None):
    title, code, official, field, search, words = o
    return {"title": title, "anzsco": code, "anzscoTitle": official, "field": field, "searchTitle": search, "score": round(score, 1), "reasons": reasons or [],
            "keywords": words + FIELD_WORDS.get(field, [])}


def relevant(role: dict, occ: dict) -> bool:
    """Default guess only: the person confirms which roles are relevant on the review screen."""
    title = (role.get("title") or "").lower()
    body = " ".join(role.get("bullets", [])).lower()
    words = occ.get("keywords", [])
    head = occ["title"].lower().split()[0]
    return head in title or any(w in title for w in words) or sum(1 for w in words if w in body) >= 3


def suggest(resume: dict, limit=4):
    """Rank occupations from where evidence is strongest: summary, degree major, relevant titles, projects, then skills."""
    summary = (resume.get("summary") or "").lower()
    lead = re.split(r"(?<=\.)\s", summary, maxsplit=1)[0]
    edu = " ".join(f"{e.get('degree', '')} {e.get('major', '')}" for e in resume.get("education", []) if e.get("level") != "secondary").lower()
    roles = [r for r in resume.get("experience", [])]
    projects = " ".join(f"{p.get('name', '')} {' '.join(p.get('tools', []))} {' '.join(p.get('bullets', []))}" for p in resume.get("projects", [])).lower()
    skills = " ".join(s for g in resume.get("skillGroups", []) for s in g.get("items", [])).lower()
    results = []
    for o in CATALOGUE:
        title, _, _, _, _, words = o
        title_l = title.lower()
        head = re.escape(title_l.split()[0].rstrip("s"))
        score, reasons = 0.0, []
        if re.search(head, lead):
            score += 6; reasons.append("Your summary describes you this way")
        hits = [w for w in words if w in summary]
        score += 1.5 * len(hits)
        if re.search(head, edu):
            score += 6; reasons.append("Matches your degree major")
        score += 1.2 * sum(1 for w in words if w in edu)
        for i, r in enumerate(roles):
            weight = 1.0 / (1 + i * 0.35)
            t = (r.get("title") or "").lower()
            if re.search(head, t) or title_l in t:
                score += 4 * weight
                reasons.append(f"Role: {r.get('title')}")
            score += 0.4 * weight * sum(1 for w in words if w in " ".join(r.get("bullets", [])).lower())
        p_hits = [w for w in words if w in projects]
        if p_hits:
            score += 0.9 * len(p_hits); reasons.append(f"Projects show {', '.join(p_hits[:3])}")
        score += 0.35 * sum(1 for w in words if w in skills)
        if score > 0:
            results.append(entry(o, score, list(dict.fromkeys(reasons))[:3]))
    results.sort(key=lambda x: -x["score"])
    return results[:limit]


def catalogue_payload():
    return [entry(o) for o in CATALOGUE]
