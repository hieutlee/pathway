"""Section-aware resume parser.

The resume is split into its own sections first (Experience, Education, Projects, Volunteering...),
then each section is read as entries anchored on date ranges. Durations come only from those
entry date ranges, never from stray years elsewhere in the text (standards like AS 4254.2-2012,
certification years or high-school dates). Every extracted item is returned for the person to
confirm or correct before anything downstream uses it.
"""
from __future__ import annotations

import re
from datetime import date

import migration_rules as R
import occupations

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
POINT = rf"(?:{MONTH_RE}\s*(?:19|20)\d{{2}}|(?:0?[1-9]|1[0-2])/(?:19|20)\d{{2}}|(?:19|20)\d{{2}})"
END = rf"(?:{POINT}|present|current|now|today|ongoing)"
RANGE_RE = re.compile(rf"({POINT})\s*(?:–|—|-|to|until)\s*({END})", re.I)
BULLET_RE = re.compile(r"^\s*(?:[•●▪◦·\-–*‣■□➢✓]|\d+\.)\s*")

SECTIONS = {
    "summary": r"summary|profile|professional summary|career objective|objective|about me|career profile",
    "education": r"education|education and training|academic background|qualifications|academic qualifications",
    "experience": r"experience|work experience|professional experience|employment|employment history|work history|career history|relevant experience|industry experience",
    "projects": r"projects|project experience|academic projects|key projects|personal projects|selected projects|engineering projects",
    "volunteering": r"volunteering|volunteer experience|volunteer work|community involvement|extracurricular|leadership and volunteering|extra-curricular activities",
    "skills": r"skills|technical skills|key skills|core skills|skills and tools|technical competencies|competencies",
    "certifications": r"certifications|certificates|licenses and certifications|licences and certifications|professional development|courses|training",
    "achievements": r"achievements|awards|honours|honors|awards and achievements|achievements and awards|accomplishments",
    "publications": r"publications|thesis|research|papers|research publications",
    "references": r"references|referees",
    "other": r"availability.*|interests|hobbies|languages|additional information|licen[cs]es.*",
}
HEADING = {key: re.compile(rf"^(?:{pat})\s*:?$", re.I) for key, pat in SECTIONS.items()}

AU_PLACES = {"brisbane": "QLD", "gold coast": "QLD", "sunshine coast": "QLD", "toowoomba": "QLD", "townsville": "QLD", "cairns": "QLD", "ipswich": "QLD", "logan": "QLD",
             "sydney": "NSW", "newcastle": "NSW", "wollongong": "NSW", "parramatta": "NSW", "melbourne": "VIC", "geelong": "VIC", "ballarat": "VIC", "adelaide": "SA",
             "perth": "WA", "hobart": "TAS", "launceston": "TAS", "canberra": "ACT", "darwin": "NT"}
STATE_WORDS = {"qld": "QLD", "queensland": "QLD", "nsw": "NSW", "new south wales": "NSW", "vic": "VIC", "victoria": "VIC", "sa": "SA", "south australia": "SA",
               "wa": "WA", "western australia": "WA", "tas": "TAS", "tasmania": "TAS", "act": "ACT", "nt": "NT", "northern territory": "NT", "australia": ""}
OVERSEAS_PLACES = ["ho chi minh city", "hanoi", "da nang", "singapore", "kuala lumpur", "jakarta", "bangkok", "manila", "mumbai", "delhi", "bangalore", "bengaluru",
                   "chennai", "hyderabad", "shanghai", "beijing", "shenzhen", "hong kong", "taipei", "seoul", "tokyo", "dhaka", "kathmandu", "colombo", "karachi", "lahore",
                   "london", "dubai", "auckland", "wellington", "vietnam", "india", "china", "nepal", "indonesia", "malaysia", "philippines", "thailand", "pakistan"]
REMOTE = ["remote", "hybrid"]
ACHIEVEMENT_WORDS = r"selected|top\s*\d+|\d+\s*of\s*\d+|award|prize|scholarship|dean'?s|high distinction|first place|winner|recogni[sz]ed|showcase|finalist|medal|honou?r roll|published|patent"
INTERN_WORDS = r"intern|internship|vacation|placement|work experience student|cadet"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def tidy(text: str) -> str:
    text = text.replace(" ", " ").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def split_glued(line: str) -> str:
    """PDF extraction often glues columns: 'Queensland University of TechnologyBrisbane City'."""
    return re.sub(r"(?<=[a-z\)])(?=[A-Z][a-z])", " | ", line)


def parse_point(text: str, is_end=False):
    t = text.strip().lower().rstrip(".")
    if re.fullmatch(r"present|current|now|today|ongoing", t):
        return None, True
    m = re.match(rf"({MONTH_RE})\s*((?:19|20)\d{{2}})", t)
    if m:
        return date(int(m[2]), MONTHS[m[1][:3]], 1), False
    m = re.match(r"(\d{1,2})/((?:19|20)\d{2})", t)
    if m:
        return date(int(m[2]), int(m[1]), 1), False
    m = re.match(r"((?:19|20)\d{2})", t)
    if m:
        return date(int(m[1]), 12 if is_end else 1, 1), False
    return None, False


def month_diff(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + b.month - a.month


def fmt_months(m: int) -> str:
    y, mo = divmod(max(0, m), 12)
    parts = ([f"{y} yr{'s' if y != 1 else ''}"] if y else []) + ([f"{mo} mo{'s' if mo != 1 else ''}"] if mo else [])
    return " ".join(parts) or "Less than 1 month"


def place_of(text: str):
    t = (text or "").lower()
    if any(w in t for w in REMOTE):
        return "remote", ""
    for place, st in AU_PLACES.items():
        if place in t:
            return "australia", st
    for word, st in STATE_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", t):
            return "australia", st
    if any(p in t for p in OVERSEAS_PLACES):
        return "overseas", ""
    return "unknown", ""


def split_org_location(line: str):
    """'Mercedes-Benz GroupHo Chi Minh City' -> ('Mercedes-Benz Group', 'Ho Chi Minh City')."""
    line = split_glued(line.strip())
    if " | " in line:
        org, _, loc = line.partition(" | ")
        return org.strip(" ,|"), loc.replace(" | ", " ").strip(" ,|")
    low = line.lower()
    candidates = sorted(list(AU_PLACES) + OVERSEAS_PLACES + REMOTE + ["brisbane city", "sydney cbd", "melbourne cbd"], key=len, reverse=True)
    for place in candidates:
        idx = low.rfind(place)
        if idx > 0 and low[idx:].strip(" ,.") .startswith(place):
            tail = line[idx:].strip(" ,")
            if len(tail) <= 40:
                return line[:idx].strip(" ,|-–"), tail
    m = re.match(r"^(.*?),\s*([A-Z][A-Za-z ]+(?:,\s*[A-Z]{2,3})?)$", line)
    if m and len(m[2]) < 35:
        return m[1].strip(), m[2].strip()
    return line.strip(), ""


# ---------------------------------------------------------------------------
# Sectioning
# ---------------------------------------------------------------------------

def sections(lines):
    out, current = {"_top": []}, "_top"
    for line in lines:
        clean = line.strip().strip(":").strip()
        key = next((k for k, rx in HEADING.items() if len(clean) <= 48 and rx.match(clean)), None)
        if key:
            current = key if key not in out else key  # merge repeated headings
            out.setdefault(current, [])
            continue
        out.setdefault(current, []).append(line)
    return out


def entries(lines, kind):
    """Group lines into entries anchored on date ranges; bullets and wrapped lines attach to the entry."""
    items, cur = [], None
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        rng = RANGE_RE.search(line)
        is_bullet = bool(BULLET_RE.match(line)) and not re.match(r"^\d+\.\d", line)
        if rng and not is_bullet:
            head = line[:rng.start()].strip(" |,–-")
            org_line = None
            if cur and cur.get("pendingHeader"):
                org_line = cur.pop("pendingHeader")
            elif items and items[-1].get("_last_plain") and not items[-1]["_last_plain"].endswith((".", ";")):
                prev = items[-1]
                # the previous plain line belongs to this entry header, not to the last bullet
                org_line = prev.pop("_last_plain")
                if prev["bullets"] and prev["bullets"][-1].endswith(" " + org_line):
                    prev["bullets"][-1] = prev["bullets"][-1][: -len(org_line) - 1]
            start_d, _ = parse_point(rng[1])
            end_d, current = parse_point(rng[2], is_end=True)
            org, loc = split_org_location(org_line) if org_line else ("", "")
            title = split_glued(head).replace(" | ", " ").strip()
            if not org and " | " in split_glued(head):
                title, _, org = split_glued(head).partition(" | ")
            if not org_line and re.search(r"\s(?:at|@|,|\|)\s", head):
                parts = re.split(r"\s(?:at|@|\|)\s|,\s", head, maxsplit=1)
                title, org = parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""
            cur = {"title": title, "org": org, "location": loc, "start": start_d.isoformat() if start_d else None,
                   "end": None if current else (end_d.isoformat() if end_d else None), "current": current, "bullets": [], "dateText": rng[0]}
            items.append(cur)
            continue
        if is_bullet:
            if cur is None:
                cur = {"title": "", "org": "", "location": "", "start": None, "end": None, "current": False, "bullets": [], "dateText": ""}
                items.append(cur)
            cur["bullets"].append(BULLET_RE.sub("", line).strip())
            cur["_last_plain"] = None
            cur["_in_bullet"] = True
            continue
        # plain line: either a wrapped bullet, or a header for the next entry
        if cur and cur.get("_in_bullet") and cur["bullets"] and not looks_like_header(line, lines, i):
            cur["bullets"][-1] += " " + line
            cur["_last_plain"] = line
            continue
        if kind == "projects" or (cur is None) or looks_like_header(line, lines, i):
            # undated header line (projects, or company line before a date line)
            nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
            if RANGE_RE.search(nxt) and not BULLET_RE.match(nxt):
                cur = {"pendingHeader": line, "bullets": []}
                continue
            name, tools = header_tools(line)
            cur = {"title": name, "org": "", "location": "", "start": None, "end": None, "current": False, "bullets": [], "tools": tools, "dateText": ""}
            items.append(cur)
            continue
        if cur is not None:
            cur["bullets"].append(line)
    for it in items:
        for k in ("_last_plain", "_in_bullet", "pendingHeader"):
            it.pop(k, None)
    return [it for it in items if it.get("title") or it.get("bullets")]


def looks_like_header(line, lines, i):
    nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
    if RANGE_RE.search(nxt) and not BULLET_RE.match(nxt):
        return True
    if "|" in line and len(line) < 140 and BULLET_RE.match(nxt):
        return True
    return False


def header_tools(line):
    line = split_glued(line) if "|" not in line else line
    for sep in ("|", " — ", " – ", ": "):
        if sep in line:
            name, _, tools = line.partition(sep)
            return name.strip(), [t.strip() for t in re.split(r",|;|/(?=\s)", tools) if t.strip()]
    m = re.match(r"^(.*?)\s*\((.+)\)\s*$", line)
    if m:
        return m[1].strip(), [t.strip() for t in m[2].split(",") if t.strip()]
    return line.strip(), []


# ---------------------------------------------------------------------------
# Sections into structures
# ---------------------------------------------------------------------------

def duration(item, today):
    if not item.get("start"):
        return None
    s = date.fromisoformat(item["start"])
    e = today if item.get("current") or not item.get("end") else date.fromisoformat(item["end"])
    return max(1, month_diff(s, e) + (0 if item.get("current") else 1))


def union_months(items, today):
    spans = []
    for it in items:
        if not it.get("start"):
            continue
        s = date.fromisoformat(it["start"])
        e = today if it.get("current") or not it.get("end") else date.fromisoformat(it["end"])
        a, b = s.year * 12 + s.month, e.year * 12 + e.month + (0 if it.get("current") else 1)
        spans.append((a, b))
    spans.sort()
    total, cur_a, cur_b = 0, None, None
    for a, b in spans:
        if cur_b is None or a > cur_b:
            if cur_b is not None:
                total += cur_b - cur_a
            cur_a, cur_b = a, b
        else:
            cur_b = max(cur_b, b)
    if cur_b is not None:
        total += cur_b - cur_a
    return total


def education_entries(lines):
    out = []
    for it in entries(lines, "education"):
        degree = it["title"]
        institution, loc = it["org"], it["location"]
        low = degree.lower()
        level = ("doctorate" if re.search(r"ph\.?d|doctor of", low) else "masters_research" if re.search(r"master of (?:philosophy|research)|mphil|by research", low)
                 else "masters_coursework" if re.search(r"master|mba|msc|meng", low) else "bachelor" if re.search(r"bachelor|honours|b\.\s?eng|bsc|\bba\b", low)
                 else "diploma" if "diploma" in low else "trade" if re.search(r"certificate (?:iii|iv)", low)
                 else "secondary" if re.search(r"high school|certificate of education|hsc|vce|qce|a-levels|year 12|secondary", low + " " + institution.lower()) else "other")
        major, honours = "", bool(re.search(r"honou?rs", low))
        m = re.match(r"^(.*?(?:\([^)]*\))?)\s*(?:,|–|-|—|\bin\b|majoring in|major:?)\s*(.+)$", degree, re.I)
        if m and level not in {"secondary"}:
            base, rest = m[1].strip(), m[2].strip()
            if re.search(r"bachelor|master|diploma|doctor|certificate", base, re.I):
                degree, major = base, rest
        mm = re.search(r"(?:major(?:ing)?(?: in)?|specialis(?:ation|ing) in|concentration)\s*:?\s*([^.;]+)", " ".join(it["bullets"]), re.I)
        if mm and not major:
            major = mm[1].strip()
        kind, state = place_of(f"{institution} {loc}")
        inst_hit = next(((name, st, reg) for name, (st, reg) in R.INSTITUTIONS.items() if name in institution.lower()), None)
        if inst_hit:
            kind, state = "australia", inst_hit[1]
        achievements = [b for b in it["bullets"] if re.search(ACHIEVEMENT_WORDS, b, re.I)]
        out.append({"degree": degree, "major": major, "honours": honours, "institution": institution, "location": loc, "level": level,
                    "start": it["start"], "end": it["end"], "current": it["current"], "australian": kind == "australia", "state": state,
                    "regionalCampus": (inst_hit[2] if inst_hit else "no"), "notes": it["bullets"], "achievements": achievements})
    return out


def experience_entries(lines, today, volunteer=False):
    out = []
    for it in entries(lines, "experience"):
        if not it.get("start") and not it.get("title"):
            continue
        title, org = it["title"], it["org"]
        is_vol = volunteer or bool(re.search(r"volunteer|pro bono|unpaid", f"{title} {org}", re.I))
        kind, state = place_of(f"{org} {it['location']}")
        out.append({"title": title, "org": org, "location": it["location"], "where": kind, "state": state, "start": it["start"], "end": it["end"],
                    "current": it["current"], "months": duration(it, today), "bullets": it["bullets"], "volunteer": is_vol,
                    "internship": bool(re.search(INTERN_WORDS, title, re.I)) or bool(re.search(r"undergraduate|student", title, re.I))})
    return out


def skill_groups(lines):
    groups, loose = [], []
    for raw in lines:
        line = BULLET_RE.sub("", raw.strip())
        if not line:
            continue
        m = re.match(r"^([A-Za-z &/+\-]{2,40}?)\s*:{1,2}\s*(.+)$", line)
        if m:
            items = [x.strip(" .") for x in re.split(r",|;|•|\|", m[2]) if x.strip(" .")]
            groups.append({"name": m[1].strip(), "items": items})
        elif groups and not re.search(r":", line):
            groups[-1]["items"] += [x.strip(" .") for x in re.split(r",|;|•|\|", line) if x.strip(" .")]
        else:
            loose += [x.strip(" .") for x in re.split(r",|;|•|\|", line) if x.strip(" .")]
    if loose:
        groups.append({"name": "Skills", "items": loose})
    return groups


def paragraph_items(lines):
    items, buf = [], []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if BULLET_RE.match(line):
            if buf: items.append(" ".join(buf)); buf = []
            buf = [BULLET_RE.sub("", line)]
        else:
            buf.append(line)
            if line.endswith(".") and len(" ".join(buf)) > 60:
                items.append(" ".join(buf)); buf = []
    if buf:
        items.append(" ".join(buf))
    return items


def certification_items(lines):
    out = []
    for raw in lines:
        line = BULLET_RE.sub("", raw.strip())
        if not line:
            continue
        m = re.match(r"^(.*?):\s*(.+?)(?:\s*\(([^)]*)\))?\s*$", line)
        if m and len(m[1]) < 60:
            out.append({"issuer": m[1].strip(), "name": m[2].strip(), "date": (m[3] or "").strip()})
        else:
            d = re.search(rf"\(?({MONTH_RE}\s*(?:19|20)\d{{2}}|(?:19|20)\d{{2}})\)?\s*$", line, re.I)
            out.append({"issuer": "", "name": line[:d.start()].strip(" -–,(") if d else line, "date": d[1] if d else ""})
    return out


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse(text: str, today: date | None = None) -> dict:
    today = today or date.today()
    text = tidy(text)
    lines = [l.rstrip() for l in text.splitlines()]
    nonempty = [l.strip() for l in lines if l.strip()]
    sec = sections(lines)
    top = [l.strip() for l in sec.get("_top", []) if l.strip()]

    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone = re.search(r"(?:\+?61\s?|0)4\d{2}\s?\d{3}\s?\d{3}|(?:\+?61\s?|0)[2378]\s?\d{4}\s?\d{4}|\+\d{1,3}[\s\d]{8,14}", text)
    linkedin = re.search(r"linkedin\.com/in/[\w-]+", text, re.I)
    name = next((l for l in (top or nonempty)[:4] if 2 <= len(l.split()) <= 5 and not re.search(r"[@\d|]|resume|curriculum|vitae", l, re.I)), "")

    summary = " ".join(l.strip() for l in sec.get("summary", []) if l.strip())
    education = education_entries(sec.get("education", []))
    experience = experience_entries(sec.get("experience", []), today)
    volunteering = experience_entries(sec.get("volunteering", []), today, volunteer=True)
    moved = [e for e in experience if e["volunteer"]]
    experience = [e for e in experience if not e["volunteer"]]
    volunteering = moved + volunteering
    projects = []
    for it in entries(sec.get("projects", []), "projects"):
        name_, tools = (it["title"], it.get("tools", []))
        if not tools and "|" in name_:
            name_, tools = header_tools(name_)
        projects.append({"name": name_, "tools": tools, "bullets": it["bullets"], "start": it.get("start"), "end": it.get("end")})
    groups = skill_groups(sec.get("skills", []))
    if not any(g["items"] for g in groups):
        groups = inferred_skills(experience + volunteering, projects, summary)
    certs = certification_items(sec.get("certifications", []))
    publications = paragraph_items(sec.get("publications", []))
    achievements = []
    for a in paragraph_items(sec.get("achievements", [])):
        achievements.append({"text": a, "source": "Achievements"})
    for e in education:
        for a in e["achievements"]:
            achievements.append({"text": a, "source": e["institution"] or e["degree"]})
    for s in re.split(r"(?<=\.)\s+", summary):
        if re.search(ACHIEVEMENT_WORDS, s, re.I) and not any(s[:40] in a["text"] for a in achievements):
            achievements.append({"text": s.strip(), "source": "Summary"})
    for p in publications:
        achievements.append({"text": p, "source": "Publication"})
    other = [BULLET_RE.sub("", l.strip()) for l in sec.get("other", []) if l.strip()]
    licences = [l for l in other if re.search(r"licen[cs]e", l, re.I)]

    english = None
    m = re.search(r"ielts[^0-9\n]{0,30}(\d(?:\.5)?)", text, re.I) or re.search(r"pte(?: academic)?[^0-9\n]{0,30}(\d{2})", text, re.I)
    if m:
        english = m[0]

    # Location: explicit Australian place in the header, else most recent Australian role or study.
    location, loc_basis = "", ""
    head_text = " ".join(top[:4])
    kind, st = place_of(head_text)
    if kind == "australia" and st:
        city = next((p.title() for p in AU_PLACES if p in head_text.lower()), "")
        location, loc_basis = f"{city + ', ' if city else ''}{st}", "Resume header"
    else:
        for e in sorted(experience, key=lambda x: x.get("start") or "", reverse=True) + sorted(volunteering, key=lambda x: x.get("start") or "", reverse=True):
            if e["where"] == "australia" and e["state"]:
                city = next((p.title() for p in AU_PLACES if p in f"{e['org']} {e['location']}".lower()), "")
                location, loc_basis = f"{city + ', ' if city else ''}{e['state']}", f"Most recent Australian role ({e['org']})"
                break
        if not location:
            au_edu = next((e for e in education if e["australian"] and e["state"]), None)
            if au_edu:
                city = next((p.title() for p in AU_PLACES if p in f"{au_edu['institution']} {au_edu['location']}".lower()), "")
                location, loc_basis = f"{city + ', ' if city else ''}{au_edu['state']}", f"Study at {au_edu['institution']}"

    resume = {"name": name, "contact": {"email": email[0] if email else "", "phone": phone[0].strip() if phone else "", "linkedin": linkedin[0] if linkedin else ""},
              "location": location, "locationBasis": loc_basis, "summary": summary, "education": education, "experience": experience, "volunteering": volunteering,
              "projects": projects, "skillGroups": groups, "certifications": certs, "publications": publications, "achievements": achievements, "licences": licences,
              "other": [o for o in other if o not in licences], "english": english,
              "sectionsFound": [k for k in sec if k != "_top" and sec[k]]}
    resume["suggestions"] = occupations.suggest(resume)
    best = resume["suggestions"][0] if resume["suggestions"] else None
    for e in resume["experience"]:
        e["relevant"] = occupations.relevant(e, best) if best else False
    resume["warnings"] = warnings(resume)
    return resume


def inferred_skills(roles, projects, summary):
    """No skills section: conclude skills from what the person describes doing, with the source kept."""
    from job_analysis import mentions
    found = {}
    for r in roles:
        for m in mentions(f"{r.get('title','')}. {' '.join(r.get('bullets', []))}"):
            found.setdefault(m["skill"], f"{r.get('title') or 'a role'}")
    for p in projects:
        for m in mentions(f"{p.get('name','')}. {' '.join(p.get('tools', []))}. {' '.join(p.get('bullets', []))}"):
            found.setdefault(m["skill"], f"project {p.get('name')}")
        for t in p.get("tools", []):
            found.setdefault(t, f"project {p.get('name')}")
    for m in mentions(summary or ""):
        found.setdefault(m["skill"], "your summary")
    if not found:
        return []
    return [{"name": "Found in your experience", "items": list(found)[:30], "inferred": True, "sources": found}]


def warnings(resume):
    w = []
    if not resume["experience"]:
        w.append("No paid experience entries with dates were found. Add your roles so experience can be counted.")
    undated = [e for e in resume["experience"] if not e.get("start")]
    if undated:
        w.append(f"{len(undated)} role(s) have no dates, so they are not counted in totals.")
    if not resume["education"]:
        w.append("No education entries were found.")
    if any(g.get("inferred") for g in resume["skillGroups"]):
        w.append("No skills section was found, so skills were concluded from your experience and projects. Check them below.")
    if not resume["projects"]:
        w.append("No projects were found. Graduates often rely on projects as evidence, so add your strongest ones.")
    return w


def summarise_experience(experience, relevant_flags, today, qualification_end=None):
    """Totals for the review screen: union of paid roles, relevant roles, and post-qualification relevant roles."""
    paid = [e for e in experience if not e.get("volunteer")]
    relevant = [e for e, flag in zip(experience, relevant_flags) if flag and not e.get("volunteer")]
    def post(items):
        if not qualification_end:
            return items
        out = []
        for e in items:
            if not e.get("start"):
                continue
            s = max(date.fromisoformat(e["start"]), qualification_end)
            end = today if e.get("current") or not e.get("end") else date.fromisoformat(e["end"])
            if end > s:
                out.append({**e, "start": s.isoformat()})
        return out
    after = post(relevant)
    return {"paidMonths": union_months(paid, today), "relevantMonths": union_months(relevant, today), "postQualificationMonths": union_months(after, today),
            "postQualificationAustraliaMonths": union_months([e for e in after if e.get("where") in {"australia", "remote"}], today),
            "postQualificationOverseasMonths": union_months([e for e in after if e.get("where") == "overseas"], today)}
