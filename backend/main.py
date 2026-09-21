from __future__ import annotations
import io, os, re, time
from datetime import datetime, timezone
from typing import Any
import httpx
from urllib.parse import urljoin
from openpyxl import load_workbook
from bs4 import BeautifulSoup
from cachetools import TTLCache
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document

app = FastAPI(title="Pathway Live Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"] , allow_methods=["*"] , allow_headers=["*"])

CACHE = {
    "migration": TTLCache(maxsize=64, ttl=60*60),
    "occupation": TTLCache(maxsize=128, ttl=60*60*12),
    "vacancies": TTLCache(maxsize=128, ttl=60*60*6),
    "jobs": TTLCache(maxsize=128, ttl=60*15),
}

HOME_AFFAIRS = "https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect/invitation-rounds"
JSA_OCCUPATIONS = "https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles"
JSA_SHORTAGE = "https://www.jobsandskills.gov.au/data/occupation-shortage/occupation-shortage-list"
JSA_SHORTAGE_HOME = "https://www.jobsandskills.gov.au/data/occupation-shortage"
JSA_SHORTAGE_REPORT = "https://www.jobsandskills.gov.au/research/occupation-shortage-report"
JSA_IVI = "https://www.jobsandskills.gov.au/data/internet-vacancy-index"
ABS_OSCA = "https://www.abs.gov.au/statistics/classifications/osca-occupation-standard-classification-australia"

MIGRATION_PATHWAY_LINKS = {
    "189": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189",
    "190": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-nominated-190",
    "491": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-work-regional-provisional-491",
    "482": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skills-in-demand-482",
    "186": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
    "494": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
    "191": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/permanent-residence-skilled-regional-191",
    "485": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485",
    "407": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407",
    "858": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/national-innovation-858",
}

HEADERS={"User-Agent":"PathwayDemo/0.1 (+career-intelligence-demo)"}

def now_iso(): return datetime.now(timezone.utc).isoformat()
def age_label(ts: float):
    mins=max(0,int((time.time()-ts)/60))
    if mins < 1: return "Updated just now"
    if mins < 60: return f"Updated {mins} minutes ago"
    return f"Updated {mins//60} hours ago"

def cache_get(bucket: str, key: str):
    item=CACHE[bucket].get(key)
    if not item: return None
    payload=dict(item["payload"])
    payload["status"]="cached"
    payload["freshness"]=age_label(item["ts"])
    return payload

def cache_put(bucket: str, key: str, payload: dict):
    CACHE[bucket][key]={"payload":payload,"ts":time.time()}
    return payload

async def fetch_html(url: str, timeout=10):
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
        r=await client.get(url)
        r.raise_for_status()
        return r.text

async def fetch_bytes(url: str, timeout=15):
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
        r=await client.get(url)
        r.raise_for_status()
        return r.content

def norm_occ(value: str):
    return re.sub(r'[^a-z0-9]+',' ',str(value or '').lower()).strip()

def parse_osl_workbook(raw: bytes, occupation: str, state: str):
    target=norm_occ(occupation)
    if not target: return None
    wb=load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    aliases={"QLD":["qld","queensland"],"NSW":["nsw","new south wales"],"VIC":["vic","victoria"],"WA":["wa","western australia"],"SA":["sa","south australia"],"TAS":["tas","tasmania"],"ACT":["act","australian capital territory"],"NT":["nt","northern territory"]}
    best=None
    for ws in wb.worksheets:
        rows=ws.iter_rows(values_only=True)
        buffered=[]
        header=None
        for _ in range(30):
            try: row=next(rows)
            except StopIteration: break
            buffered.append(row)
            vals=[norm_occ(v) for v in row]
            if any(v in {"occupation","occupation title","anzsco occupation","osca occupation"} or "occupation title" in v for v in vals) and any("national" in v for v in vals):
                header=[str(v or '').strip() for v in row]; break
        if not header: continue
        lower=[norm_occ(x) for x in header]
        occ_cols=[i for i,h in enumerate(lower) if "occupation" in h and "code" not in h]
        nat_cols=[i for i,h in enumerate(lower) if h in {"national","australia","national rating","national shortage rating"} or ("national" in h and "rating" in h)]
        state_cols=[i for i,h in enumerate(lower) if any(a==h or a in h for a in aliases.get(state.upper(),[]))]
        code_cols=[i for i,h in enumerate(lower) if "code" in h and ("anzsco" in h or "osca" in h or h=="code")]
        if not occ_cols: continue
        for row in rows:
            names=[str(row[i] or '').strip() for i in occ_cols if i < len(row)]
            for name in names:
                n=norm_occ(name)
                if not n: continue
                exact=n==target
                contains=target in n or n in target
                if not (exact or contains): continue
                rec={"occupation":name,"code":next((str(row[i]).strip() for i in code_cols if i<len(row) and row[i] is not None),None),
                     "nationalRating":next((str(row[i]).strip() for i in nat_cols if i<len(row) and row[i] is not None),None),
                     "stateRating":next((str(row[i]).strip() for i in state_cols if i<len(row) and row[i] is not None),None),
                     "state":state.upper(),"matchType":"exact" if exact else "close"}
                if exact: return rec
                best=best or rec
    return best

@app.get("/api/health")
def health(): return {"ok":True,"time":now_iso()}

@app.post("/api/profile/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    raw=await file.read()
    name=(file.filename or "").lower()
    text=""
    try:
        if name.endswith(".pdf"):
            reader=PdfReader(io.BytesIO(raw)); text="\n".join((p.extract_text() or "") for p in reader.pages)
        elif name.endswith(".docx"):
            doc=Document(io.BytesIO(raw)); text="\n".join(p.text for p in doc.paragraphs)
        else: text=raw.decode("utf-8",errors="ignore")
    except Exception:
        text=raw.decode("utf-8",errors="ignore")

    lines=[x.strip() for x in text.splitlines() if x.strip()]
    first=next((x for x in lines if 2<=len(x.split())<=5 and not re.search(r'@|http|resume|curriculum',x,re.I)), "Your profile")

    skill_vocab=[
        "C++","Python","C","C#","Java","JavaScript","TypeScript","React","Vue","Angular","Node.js","HTML","CSS","SQL",
        "MATLAB","Simulink","SolidWorks","CAD","PLC","Embedded systems","Firmware","RTOS","Control systems","CUDA","Linux","Git",
        "AWS","Azure","TensorFlow","PyTorch","Electronics","PCB","ROS","Excel","Power BI","Tableau","Salesforce","MYOB","Xero",
        "Financial modelling","Marketing","SEO","Google Analytics","Customer service","Project management","Accounting","Bookkeeping",
        "Data analysis","Machine learning","Nursing","Patient care","Clinical care","AutoCAD","Revit","Figma","UX","UI design"
    ]
    skills=[s for s in skill_vocab if re.search(rf'(?<!\w){re.escape(s)}(?!\w)',text,re.I)]
    degree_match=re.search(r'(Bachelor[^\n,]{0,100}|Master[^\n,]{0,100}|PhD[^\n,]{0,100}|Diploma[^\n,]{0,100}|Certificate[^\n,]{0,100})',text,re.I)

    role_families=[
        {"family":"Web and software development","occupation":"Software Developer","roles":["Web Developer","Frontend Developer","Full Stack Developer","Software Developer","Junior Software Engineer"],"keywords":["javascript","typescript","react","vue","angular","node","html","css","web developer","frontend","full stack","software developer","github"]},
        {"family":"Data and analytics","occupation":"Data Analyst","roles":["Data Analyst","Business Intelligence Analyst","Junior Data Scientist","Reporting Analyst","Analytics Consultant"],"keywords":["data analyst","data analysis","sql","power bi","tableau","python","analytics","machine learning","statistics"]},
        {"family":"Business and consulting","occupation":"Business Analyst","roles":["Graduate Business Analyst","Business Analyst","Operations Analyst","Junior Consultant","Commercial Analyst"],"keywords":["business","commerce","business analyst","operations","consulting","commercial","stakeholder","process improvement","excel","power bi"]},
        {"family":"Marketing and communications","occupation":"Marketing Specialist","roles":["Marketing Coordinator","Digital Marketing Coordinator","Marketing Analyst","Content Coordinator","Customer Insights Analyst"],"keywords":["marketing","seo","campaign","social media","google analytics","content","brand","communications","customer insights"]},
        {"family":"Accounting and finance","occupation":"Accountant","roles":["Graduate Accountant","Assistant Accountant","Financial Analyst","Accounts Officer","Junior Management Accountant"],"keywords":["accounting","accountant","finance","financial","bookkeeping","xero","myob","audit","tax","financial modelling"]},
        {"family":"Embedded and electronics","occupation":"Embedded Systems Engineer","roles":["Embedded Software Engineer","Firmware Engineer","Electronics Engineer","IoT Engineer","Junior Robotics Engineer"],"keywords":["embedded","firmware","rtos","microcontroller","stm32","esp32","pcb","electronics","c++","c language","uart","spi","i2c"]},
        {"family":"Mechatronics and automation","occupation":"Mechatronics Engineer","roles":["Mechatronics Engineer","Automation Engineer","Controls Engineer","Robotics Engineer","Systems Engineer"],"keywords":["mechatronics","plc","control systems","simulink","matlab","robotics","automation","solidworks","cad"]},
        {"family":"Mechanical engineering","occupation":"Mechanical Engineer","roles":["Mechanical Engineer","Graduate Mechanical Engineer","Design Engineer","Manufacturing Engineer","Project Engineer"],"keywords":["mechanical engineer","solidworks","mechanical design","fea","manufacturing","cad","thermodynamics"]},
        {"family":"Electrical engineering","occupation":"Electrical Engineer","roles":["Electrical Engineer","Graduate Electrical Engineer","Controls Engineer","Power Systems Engineer","Electronics Engineer"],"keywords":["electrical engineer","power systems","circuit","electronics","plc","control systems","pcb"]},
        {"family":"Civil and construction","occupation":"Civil Engineer","roles":["Graduate Civil Engineer","Civil Engineer","Site Engineer","Project Engineer","Structural Engineer"],"keywords":["civil engineer","construction","structural","autocad","revit","site engineer","infrastructure"]},
        {"family":"Nursing and healthcare","occupation":"Registered Nurse","roles":["Registered Nurse","Graduate Nurse","Clinical Nurse","Aged Care Nurse","Community Nurse"],"keywords":["registered nurse","nursing","patient care","clinical","hospital","aged care","healthcare"]},
        {"family":"Project and operations","occupation":"Project Coordinator","roles":["Project Coordinator","Project Officer","Operations Coordinator","Junior Project Manager","Program Coordinator"],"keywords":["project management","project coordinator","project officer","program","operations coordinator","schedule","stakeholder"]}
    ]

    lower=text.lower()
    scored=[]
    for fam in role_families:
        score=sum(2 if " " in kw else 1 for kw in fam["keywords"] if kw in lower)
        if score:
            scored.append((score,fam))
    scored.sort(key=lambda x:x[0], reverse=True)
    if scored:
        best=scored[0][1]
        occupation=best["occupation"]
        role_candidates=[]
        for score,fam in scored[:3]:
            confidence=min(96,55+score*7)
            for role in fam["roles"][:3]:
                role_candidates.append({"title":role,"confidence":confidence,"family":fam["family"]})
        seen=set(); role_candidates=[r for r in role_candidates if not (r["title"] in seen or seen.add(r["title"]))][:8]
        career_family=best["family"]
    else:
        occupation="General professional"
        career_family="General professional"
        role_candidates=[{"title":"Graduate Program","confidence":55,"family":"General"},{"title":"Entry Level Professional","confidence":50,"family":"General"}]

    years=[int(m.group(1)) for m in re.finditer(r'\b(20\d{2})\b',text)]
    exp=max(0,min(15,(max(years)-min(years)) if len(years)>1 else 0))
    return {
        "name":first,
        "occupation":occupation,
        "careerFamily":career_family,
        "roleCandidates":role_candidates,
        "education":degree_match.group(1).strip() if degree_match else "Qualification detected from resume",
        "experienceYears":exp,
        "skills":skills[:16] or ["Add skills from resume"],
        "goal":f"Build a meaningful Australian career in {career_family.lower()} and understand realistic migration options"
    }

@app.get("/api/intelligence/migration")
async def migration(occupation: str=Query(""), state: str=Query("QLD"), anzsco: str=Query(""), visa: str=Query(""), experienceYears: float=Query(0), education: str=Query("")):
    key="rounds"
    if cached:=cache_get("migration",key): return enrich_migration(cached,occupation,visa,experienceYears,education,state)
    try:
        html=await fetch_html(HOME_AFFAIRS)
        text=BeautifulSoup(html,"html.parser").get_text(" ",strip=True)
        date_match=re.search(r'Invitations issued on\s+([0-9]{1,2}\s+[A-Za-z]+\s+20\d{2})',text,re.I)
        inv_match=re.search(r'Skilled Independent visa\s*\(subclass 189\)\s*([0-9,]{3,})',text,re.I)
        next_match=re.search(r'next invitation round[^.]{0,180}?(?:by\s+)?([0-9]{1,2}\s+[A-Za-z]+\s+20\d{2})',text,re.I)
        tie_match=re.search(r'Skilled Independent visa\s*\(subclass 189\)\s*([0-9,]{3,})\s*([0-9]{1,2}/[0-9]{1,2}/20\d{2})',text,re.I)
        program_total=None
        # Current-round pages often expose monthly program-year totals. Sum only the 189 row when it is parseable.
        year_row=re.search(r'Skilled Independent visa\s*\(subclass 189\)\s*((?:[0-9,]+\s+){11}[0-9,]+)',text,re.I)
        if year_row:
            try: program_total=f"{sum(int(x.replace(',', '')) for x in year_row.group(1).split()):,}"
            except Exception: program_total=None
        payload={"status":"fresh","freshness":"Checked just now","updated":"just now","checkedAt":now_iso(),"source":"Department of Home Affairs","sourceUrl":HOME_AFFAIRS,
                 "latestRound":{"date":date_match.group(1) if date_match else "Current round published","invitations":inv_match.group(1) if inv_match else "See official round","tieBreak":tie_match.group(2) if tie_match else None,"headline":"Latest official SkillSelect invitation outcomes checked live."},
                 "nextRound":next_match.group(1) if next_match else None,"programYear189Invitations":program_total,"rawText":text[:30000]}
        cache_put("migration",key,payload)
        return enrich_migration(payload,occupation,visa,experienceYears,education,state)
    except Exception as e:
        fallback={"status":"unavailable","freshness":"Live check failed","updated":"not updated","source":"Department of Home Affairs","sourceUrl":HOME_AFFAIRS,"latestRound":{"headline":"Home Affairs could not be reached during this request."},"error":type(e).__name__}
        return enrich_migration(fallback,occupation,visa,experienceYears,education,state)

def enrich_migration(payload:dict, occupation:str, visa:str="", experience_years:float=0, education:str="", state:str="QLD"):
    p=dict(payload); p["latestRound"]=dict(payload.get("latestRound",{}))
    raw=payload.get("rawText","")
    score=None
    if occupation and raw:
        pattern=rf'{re.escape(occupation)}\s+([0-9]{{2,3}})\b'
        m=re.search(pattern,raw,re.I)
        if m: score=m.group(1)+" points"
    p["latestRound"]["scoreForOccupation"]=score

    v=(visa or "").lower()
    exp=float(experience_years or 0)
    is_student="student visa" in v or "500" in v
    is_graduate="temporary graduate" in v or "485" in v
    is_regional=any(x in v for x in ["491","494","regional provisional"])
    is_settled=any(x in v for x in ["permanent resident","australian citizen","subclass 189","subclass 190","subclass 191","subclass 186"])
    offshore="offshore" in v or "no current australian visa" in v
    has_occ=bool(occupation and occupation.lower() not in {"general professional","skilled professional","target occupation"})
    has_qual=bool(education and "detected from resume" not in education.lower())

    def route(code,name,family,summary,needs,status,reason,priority):
        return {"code":code,"name":name,"family":family,"summary":summary,"needs":needs,"status":status,"reason":reason,"priority":priority,"url":MIGRATION_PATHWAY_LINKS[code]}

    pathways=[]
    if not is_settled:
        pathways += [
          route("189","Skilled Independent","Points tested","Permanent skilled visa without state or employer sponsorship.","EOI, eligible occupation, skills assessment, points and invitation","Investigate" if has_occ else "Needs occupation mapping",f"Relevant to compare once {occupation or 'your occupation'} and points evidence are verified.",82 if exp>=3 else 68),
          route("190","Skilled Nominated","State nominated","Permanent skilled visa requiring nomination by an Australian state or territory.","EOI, eligible occupation, skills assessment, points and state nomination","Strong comparison" if has_occ else "Needs occupation mapping",f"State nomination can make {state} and other jurisdictions important to your strategy.",88 if has_occ else 60),
          route("491","Skilled Work Regional","Regional points tested","Provisional regional skilled visa through state nomination or eligible family sponsorship.","EOI, eligible occupation, skills assessment, points and regional nomination or family sponsorship","Strong comparison" if has_occ else "Needs occupation mapping","Useful when regional location flexibility improves the set of available pathways.",86 if has_occ else 58),
          route("482","Skills in Demand","Employer sponsored","Temporary employer sponsored skilled work route.","Eligible nominated role, sponsoring employer and required skills or experience","Employer route" if exp>=1 else "Build experience first",f"Employer sponsorship becomes more credible as directly relevant {occupation or 'skilled'} experience grows.",90 if exp>=2 else 70),
          route("186","Employer Nomination Scheme","Employer sponsored permanent","Permanent employer nominated skilled pathway.","Employer nomination plus stream specific skills, employment and assessment requirements","Later employer route" if exp<3 else "Strong comparison","Worth comparing with points tested routes when an employer relationship is strong.",87 if exp>=3 else 63),
          route("494","Skilled Employer Sponsored Regional","Regional employer sponsored","Five year regional employer sponsored provisional pathway.","Regional sponsoring employer, eligible role and stream specific skills assessment requirements","Regional employer route" if exp>=1 else "Build experience first","Useful when regional employers have demand for your occupation.",83 if exp>=2 else 62),
        ]
        if is_student or is_graduate:
            pathways.append(route("485","Temporary Graduate","Graduate transition","Temporary post study work pathway for eligible recent graduates.","Eligible Australian study, stream requirements and application timing","Current transition" if is_student else "Current visa context", "This can be the bridge from study into occupation relevant Australian experience when the current rules apply.",96 if is_student else 90))
        if is_regional:
            pathways.append(route("191","Permanent Residence Skilled Regional","Regional permanent","Permanent regional pathway for eligible holders of qualifying regional provisional visas.","Qualifying regional provisional visa history and current subclass 191 criteria","Progression route","Relevant because your selected visa is already within a regional provisional pathway.",98))
        pathways.append(route("407","Training","Training and development","Temporary sponsored occupational training route rather than a general employment migration pathway.","Approved sponsor, nominated training and relevant stream requirements","Special case","Useful only when structured occupational training is the genuine purpose.",42))
        pathways.append(route("858","National Innovation","Exceptional talent","Permanent invitation based pathway for people with an internationally recognised record of exceptional achievement.","Exceptional achievement profile and invitation process","Specialist route","Not a standard skilled migration substitute, but worth showing when a profile has genuinely exceptional evidence.",30))
    else:
        pathways=[]

    pathways.sort(key=lambda x:x["priority"], reverse=True)
    p["pathways"]=pathways
    p["currentVisaContext"]={"visa":visa or "Not confirmed","settled":is_settled,"regional":is_regional,"offshore":offshore}
    p["interpretation"]={"title":"Compare routes, do not anchor on subclass 189","detail":"Subclass 189 is only one pathway. Pathway compares points tested, state nominated, employer sponsored, regional, graduate and specialist routes, then uses your profile to decide which deserve attention first."}
    p.pop("rawText",None)
    return p

@app.get("/api/intelligence/occupation")
async def occupation(occupation: str=Query(""), state: str=Query("QLD"), anzsco: str=Query("")):
    key=(occupation or anzsco or "general").lower()
    if cached:=cache_get("occupation",key): return cached
    try:
        html=await fetch_html(JSA_OCCUPATIONS)
        text=BeautifulSoup(html,"html.parser").get_text(" ",strip=True)
        shortage_html=await fetch_html(JSA_SHORTAGE)
        shortage_text=BeautifulSoup(shortage_html,"html.parser").get_text(" ",strip=True)
        shortage_home_html=await fetch_html(JSA_SHORTAGE_HOME)
        shortage_home_text=BeautifulSoup(shortage_home_html,"html.parser").get_text(" ",strip=True)
        shortage_report_html=await fetch_html(JSA_SHORTAGE_REPORT)
        shortage_report_text=BeautifulSoup(shortage_report_html,"html.parser").get_text(" ",strip=True)
        shortage="Current OSL checked"
        occupation_match=False
        osl_match=None
        try:
            soup=BeautifulSoup(shortage_home_html,"html.parser")
            xlsx_link=next((urljoin(JSA_SHORTAGE_HOME,a.get("href")) for a in soup.find_all("a",href=True) if "occupation shortage list" in (a.get_text(" ",strip=True)+" "+a.get("href","" )).lower() and a.get("href","").lower().endswith(".xlsx")),None)
            if xlsx_link:
                osl_match=parse_osl_workbook(await fetch_bytes(xlsx_link),occupation,state)
        except Exception:
            osl_match=None
        if osl_match:
            rating=(osl_match.get("nationalRating") or "").lower()
            occupation_match="shortage" in rating and "no shortage" not in rating
            shortage=osl_match.get("nationalRating") or "Occupation matched"
        elif occupation and occupation.lower() in shortage_text.lower():
            shortage="Shortage list match"; occupation_match=True
        list_year=(re.search(r'(20\d{2})\s+Occupation Shortage List',shortage_home_text,re.I) or re.search(r'(20\d{2})\s+OSL',shortage_home_text,re.I))
        national=re.search(r'(\d{1,2})%\s+of occupations[^.]{0,80}?shortage',shortage_home_text,re.I)
        counts=re.search(r'(\d{2,4})\s+(?:out of|of)\s+(\d{3,4})[^.]{0,80}?shortage',shortage_home_text,re.I)
        fill=re.search(r'(?:National vacancy fill rates? (?:fell|rose|reached|dipped)[^0-9]{0,20})(\d{2}\.\d)%',shortage_report_text,re.I)
        report_date=re.search(r'Occupation Shortage Report\s*[-–]\s*([A-Za-z]+\s+20\d{2})',shortage_report_text,re.I)
        payload={"status":"fresh","freshness":"Checked just now","updated":"just now","checkedAt":now_iso(),"source":"Jobs and Skills Australia","sourceUrl":JSA_SHORTAGE_HOME,
                 "shortage":shortage,"occupationMatch":occupation_match,"occupationChecked":occupation or "Target occupation",
                 "occupationResult":osl_match,
                 "shortageNote":"Current JSA shortage sources checked for your mapped occupation.",
                 "oslYear":list_year.group(1) if list_year else None,
                 "nationalShortagePct":(national.group(1)+"%") if national else None,
                 "nationalShortageCount":counts.group(1) if counts else None,"occupationsAssessed":counts.group(2) if counts else None,
                 "vacancyFillRate":(fill.group(1)+"%") if fill else None,"shortageReportPeriod":report_date.group(1) if report_date else None,
                 "employment":"Occupation profiles available from JSA","earnings":"Occupation profile releases are transitioning from ANZSCO to OSCA."}
        return cache_put("occupation",key,payload)
    except Exception as e:
        return {"status":"unavailable","freshness":"Live check failed","updated":"not updated","source":"Jobs and Skills Australia","sourceUrl":JSA_OCCUPATIONS,"shortage":"Unavailable","shortageNote":"The live JSA occupation source did not respond.","error":type(e).__name__}

@app.get("/api/intelligence/vacancies")
async def vacancies(occupation: str=Query(""), state: str=Query("QLD"), anzsco: str=Query("")):
    key=(occupation+state).lower()
    if cached:=cache_get("vacancies",key): return cached
    try:
        html=await fetch_html(JSA_IVI)
        text=BeautifulSoup(html,"html.parser").get_text(" ",strip=True)
        released=re.search(r'([A-Z][a-z]+\s+20\d{2})\s+data (?:were|was) released on\s+([0-9]{1,2}\s+[A-Z][a-z]+\s+20\d{2})',text,re.I)
        next_release=None
        future=re.findall(r'([A-Z][a-z]+\s+20\d{2})\s+([0-9]{1,2}\s+[A-Z][a-z]+\s+20\d{2})',text)
        if future:
            latest_month=(released.group(1) if released else '').lower()
            next_release=next(((m,d) for m,d in future if m.lower()!=latest_month),None)
        download_count=len(re.findall(r'Internet Vacancies,',text,re.I))
        # Trend remains explicitly preview-only until the structured XLSX time-series pipeline is connected.
        trend=[{"month":"Feb","value":74},{"month":"Mar","value":79},{"month":"Apr","value":77},{"month":"May","value":82},{"month":"Jun","value":84},{"month":"Jul","value":81}]
        payload={"status":"fresh","freshness":"Source checked just now","updated":"just now","checkedAt":now_iso(),"source":"Jobs and Skills Australia Internet Vacancy Index","sourceUrl":JSA_IVI,
                 "headline":released.group(1) if released else "Latest IVI release checked",
                 "subheadline":f"Released {released.group(2)}" if released else "Monthly online vacancy intelligence",
                 "releasePeriod":released.group(1) if released else None,"releaseDate":released.group(2) if released else None,
                 "nextReleasePeriod":next_release[0] if next_release else None,"nextReleaseDate":next_release[1] if next_release else None,
                 "downloadSeries":download_count or None,"coverage":"Online job advertisements across occupations, states and regions",
                 "trend":trend,"trendMode":"interface_preview"}
        return cache_put("vacancies",key,payload)
    except Exception as e:
        return {"status":"unavailable","freshness":"Live check failed","updated":"not updated","source":"JSA Internet Vacancy Index","sourceUrl":JSA_IVI,"headline":"Unavailable","subheadline":"Live vacancy source could not be reached","trend":[],"error":type(e).__name__}

@app.get("/api/intelligence/jobs")
async def jobs(
    occupation: str=Query(""),
    state: str=Query("QLD"),
    anzsco: str=Query(""),
    skills: str=Query(""),
    education: str=Query(""),
    goal: str=Query(""),
    candidates: str=Query("")
):
    skill_list=[x.strip() for x in skills.split(",") if x.strip()]
    candidate_roles=[x.strip() for x in candidates.split("|") if x.strip()]
    key=(occupation+state+skills+education+goal+candidates).lower()
    if cached:=cache_get("jobs",key): return cached

    search_roles=candidate_roles[:5] or ([occupation] if occupation and occupation not in {"General professional","Skilled professional"} else [])
    if not search_roles:
        search_roles=["Graduate Program","Entry Level Professional"]

    app_id=os.getenv("ADZUNA_APP_ID")
    app_key=os.getenv("ADZUNA_APP_KEY")
    if app_id and app_key:
        try:
            gathered=[]
            async with httpx.AsyncClient(timeout=10) as client:
                for search_role in search_roles[:3]:
                    url="https://api.adzuna.com/v1/api/jobs/au/search/1"
                    r=await client.get(url,params={"app_id":app_id,"app_key":app_key,"what":search_role,"where":state,"results_per_page":6,"content-type":"application/json"})
                    r.raise_for_status(); js=r.json()
                    for j in js.get("results",[]):
                        title=j.get("title","Role")
                        hay=(title+" "+(j.get("description") or "")).lower()
                        matched=[s for s in skill_list if s.lower() in hay]
                        candidate_bonus=10 if any(r.lower() in title.lower() or title.lower() in r.lower() for r in search_roles) else 0
                        score=min(97,68+candidate_bonus+min(18,len(matched)*4))
                        gathered.append({"title":title,"company":(j.get("company") or {}).get("display_name","Employer"),"location":(j.get("location") or {}).get("display_name",state),"match":score,"reason":f"Current vacancy matched against your inferred role family"+(f" and skills: {', '.join(matched[:4])}." if matched else "."),"url":j.get("redirect_url")})
            unique=[]; seen=set()
            for j in sorted(gathered,key=lambda x:x["match"],reverse=True):
                k=(j["title"].lower(),j["company"].lower())
                if k not in seen:
                    seen.add(k); unique.append(j)
            payload={"status":"fresh","freshness":"Checked just now","updated":"just now","checkedAt":now_iso(),"source":"Adzuna Australia API","roles":unique[:10],"searchRoles":search_roles}
            return cache_put("jobs",key,payload)
        except Exception:
            pass

    # Personalised preview when no authorised live job provider is configured.
    # Titles are selected from the resume inferred candidate roles, never from a universal engineering fallback.
    roles=[]
    base=93
    for idx,title in enumerate(search_roles[:8]):
        matched=skill_list[idx % len(skill_list)] if skill_list else None
        reason=f"Personalised preview derived from your resume profile and inferred occupation family"
        if matched: reason+=f". Your {matched} experience is one signal supporting this recommendation"
        reason+=". Configure a licensed job feed to replace this with current advertised vacancies."
        roles.append({"title":title,"company":"Live provider required","location":state if state else "Australia","match":max(68,base-idx*4),"reason":reason})
    payload={"status":"cached","freshness":"Personalised preview, live provider not configured","updated":"provider required","source":"Pathway recommendation engine","roles":roles,"count":None,"searchRoles":search_roles,"requiresConfiguration":["ADZUNA_APP_ID","ADZUNA_APP_KEY"],"note":"Recommendations are personalised from the uploaded profile. Current vacancy results require an authorised job provider."}
    return cache_put("jobs",key,payload)

class RecommendationRequest(BaseModel):
    profile: dict[str,Any]
    intelligence: dict[str,Any]

@app.post("/api/recommend")
def recommend(req: RecommendationRequest):
    p=req.profile; intel=req.intelligence or {}
    visa=(p.get("visa") or "").lower(); exp=float(p.get("experienceYears") or 0)
    occupation=(p.get("occupation") or "General professional").strip(); skills=[x for x in (p.get("skills") or []) if x and "add skills" not in x.lower()]
    education=(p.get("education") or "").strip(); goal=(p.get("goal") or "").strip(); visa_expiry=(p.get("visaExpiry") or "").strip()
    anzsco=(p.get("anzsco") or "").strip(); osca=(p.get("osca") or "").strip(); family=(p.get("careerFamily") or "").lower()
    student="student visa" in visa or "subclass 500" in visa
    graduate="temporary graduate" in visa or "subclass 485" in visa
    working_holiday="working holiday" in visa or "417" in visa or "462" in visa
    overseas=any(x in visa for x in ["offshore","outside australia","no current australian visa"])
    settled=any(x in visa for x in ["australian citizen","australian permanent resident"])
    permanent_skilled=any(x in visa for x in ["subclass 189","subclass 190","subclass 191","subclass 186","subclass 858"])
    temporary_status=not (settled or permanent_skilled or overseas)

    blockers=[]
    def add_blocker(code,title,detail,severity="Medium"):
        blockers.append({"code":code,"title":title,"detail":detail,"severity":severity})

    if occupation.lower() in {"general professional","skilled professional","target occupation"}:
        add_blocker("occupation","Target occupation is not resolved", "Your resume does not yet map confidently to a specific Australian occupation. Confirm the closest role family before relying on migration or labour market signals.", "High")
    elif not (anzsco or osca):
        add_blocker("classification","Occupation classification is not verified", f"{occupation} was inferred from your resume, but its current OSCA or ANZSCO mapping still needs verification against duties and qualification evidence.", "High")

    if len(skills) < 4:
        add_blocker("skills","Skill evidence is too thin", "The resume exposes too few concrete technical or professional skills for strong role matching. Add tools, methods, platforms and domain capabilities you can evidence.", "High")
    elif exp < 1:
        add_blocker("experience","Limited occupation relevant experience", f"Your profile currently shows less than one year of relevant experience for {occupation}. Projects, internships, placements and measurable work samples can become the fastest evidence builder.", "High")
    elif exp < 2:
        add_blocker("experience","Experience depth is still developing", f"You have about {exp:g} year of relevant experience. Stronger Australian or directly comparable evidence would improve employer confidence and future assessment readiness.", "Medium")

    if not education or "detected from resume" in education.lower():
        add_blocker("education","Qualification details need confirmation", "Confirm your qualification title, institution and completion status so Pathway can test occupation and graduate pathway alignment more reliably.", "Medium")

    if not visa or visa in {"unknown","n/a","na"}:
        add_blocker("visa","Work rights are unknown", "Add your current visa or offshore status so Pathway can separate roles you can pursue now from pathways that require a different work right.", "High")
    elif not visa_expiry and temporary_status:
        add_blocker("visa_timing","Visa timeline is incomplete", "Add the visa expiry date if known. Timing changes which career actions should happen now and which can wait.", "Medium")

    jobs=intel.get("jobs") or {}
    if jobs.get("status") != "fresh":
        add_blocker("jobs_feed","Live vacancy coverage is limited", "Current role ranking is personalised, but an authorised live job provider is not configured, so advertised vacancy counts and employer activity are not yet fully live.", "Low")

    # Keep only the most decision relevant blockers and make sure they genuinely vary by profile.
    order={"High":0,"Medium":1,"Low":2}
    blockers=sorted(blockers,key=lambda b:order.get(b["severity"],1))[:4]
    if not blockers:
        add_blocker("optimisation","No critical profile gap detected", f"Your core profile for {occupation} is reasonably complete. The next constraint is optimisation: target the strongest current roles and keep migration evidence current.", "Low")

    evidence=[]
    def task(code,title,detail,category,status="todo"):
        evidence.append({"code":code,"title":title,"detail":detail,"category":category,"status":status})

    task("occupation","Verify occupation mapping",f"Compare your actual duties and qualification with the current OSCA and ANZSCO description for {occupation}.","Occupation", "done" if (anzsco or osca) else "todo")
    task("resume","Strengthen resume evidence",f"Add quantified achievements and concrete examples that prove your strongest {occupation} capabilities.","Career evidence", "done" if len(skills)>=6 and exp>=1 else "in_progress")
    if exp < 2:
        task("experience","Create occupation relevant experience", "Prioritise internships, projects, placements, volunteering or paid work that produces verifiable duties, outcomes and references.","Experience","todo")
    else:
        task("references","Prepare employment evidence", "Collect role descriptions, references, dates, hours, duties and measurable outcomes from relevant employment.","Experience","in_progress")
    if settled or permanent_skilled:
        task("careerfocus","Focus on career progression", "Your selected status does not require Pathway to optimise around a temporary visa transition. Prioritise occupation fit, market demand and career development.","Career","in_progress")
    elif student:
        task("graduate","Check graduate transition options", "Verify current Temporary Graduate settings, qualification eligibility and timing using official Home Affairs information before planning around subclass 485.","Migration","todo")
    elif graduate:
        task("graduatework","Use graduate work rights strategically", "Prioritise occupation relevant employment, evidence quality and any assessment requirements before your current visa timeline becomes a constraint.","Migration","in_progress")
    elif working_holiday:
        task("workrights","Use current work rights strategically", "Target roles that build skilled occupation evidence before your current work rights or employer limits become a constraint.","Migration","in_progress")
    elif overseas:
        task("offshore","Build an employer ready offshore case", "Validate assessment readiness, English evidence and Australian demand before committing to a migration route.","Migration","todo")
    else:
        task("migration","Verify migration eligibility inputs", "Confirm age, English evidence, skills assessment status and visa conditions before using points or invitation history as a decision signal.","Migration","todo")
    task("market","Test the current market", f"Use current vacancies and shortage signals to compare {occupation} with adjacent roles and locations.","Market", "done" if jobs.get("status")=="fresh" else "in_progress")

    if settled or permanent_skilled:
        base_path=[
          ("Validate occupation fit","Confirm your target occupation and strongest adjacent career options from your actual evidence.","Now","High"),
          ("Target the strongest market opportunities","Use current vacancies, shortage signals and salary context to prioritise roles and locations.","0 to 3 months","High"),
          ("Close high value capability gaps","Build the specific tools, standards, portfolio evidence or leadership depth that unlocks stronger roles.","3 to 9 months","High"),
          ("Compound career progression","Reassess seniority, salary, specialisation and employer options as your evidence grows.","Ongoing","Medium")
        ]
    elif student:
        base_path=[
          ("Verify occupation and graduate fit","Confirm qualification alignment, occupation mapping and the graduate options that apply to your circumstances.","Now","High"),
          ("Build occupation relevant Australian evidence","Prioritise internships, graduate roles, projects and references that strengthen employability and assessment evidence.","0 to 12 months","High"),
          ("Prepare assessment and English evidence","Identify the assessing authority, evidence requirements and realistic timing.","6 to 18 months","Medium"),
          ("Compare skilled, state and employer routes","Recheck 189, 190, 491 and employer sponsored options using the rules and demand current at that time.","When eligible","Medium")
        ]
    elif graduate:
        base_path=[
          ("Validate occupation alignment","Confirm that your qualification, duties and target occupation tell one coherent story.","Now","High"),
          ("Build occupation relevant Australian experience","Target roles that strengthen both employer confidence and future assessment evidence.","0 to 12 months","High"),
          ("Prepare assessment and migration evidence","Collect employment evidence and verify the requirements that apply to your occupation.","3 to 12 months","Medium"),
          ("Compare longer term pathways","Recheck skilled, state and employer routes using rules and demand current at that time.","Before expiry","Medium")
        ]
    elif working_holiday:
        base_path=[
          ("Map transferable skills","Translate experience into Australian occupation language and identify close adjacent roles.","Now","High"),
          ("Target skilled employers","Prioritise employers and roles that compound toward assessed capability.","0 to 6 months","High"),
          ("Build verified work evidence","Capture duties, outcomes and references while work rights are active.","0 to 12 months","High"),
          ("Assess longer term visa options","Compare skilled and employer routes before current work rights expire.","Before expiry","Medium")
        ]
    elif overseas:
        base_path=[
          ("Validate occupation and assessment fit","Map qualifications and experience to the relevant occupation classification and assessing authority.","Now","High"),
          ("Test Australian demand","Use current vacancy, shortage and regional data to choose target markets and adjacent occupations.","0 to 3 months","High"),
          ("Build an evidence ready application","Prepare skills assessment, English evidence and employer ready positioning.","3 to 9 months","Medium"),
          ("Choose the strongest viable route","Compare employer, state and independent options only after the evidence base is credible.","When ready","Medium")
        ]
    else:
        base_path=[
          ("Audit occupation evidence","Check duties, references, qualifications and gaps against the target occupation.","Now","High"),
          ("Close Australian market gaps","Target the local tools, standards or evidence employers repeatedly request.","0 to 6 months","High"),
          ("Strengthen assessment readiness","Prepare the employment and qualification evidence needed for the relevant assessing authority.","3 to 9 months","Medium"),
          ("Recalculate pathway options","Compare current skilled, state and employer routes after evidence gaps are closed.","6 to 12 months","Medium")
        ]

    # Progress is evidence based, not time animation. It changes when the profile changes and live checks improve.
    completion=0
    if occupation.lower() not in {"general professional","skilled professional","target occupation"}: completion+=1
    if anzsco or osca: completion+=1
    if len(skills)>=4: completion+=1
    if exp>=1: completion+=1
    if education and "detected from resume" not in education.lower(): completion+=1
    if visa: completion+=1
    current_index=0 if completion<3 else 1 if completion<5 else 2 if completion<6 else 3
    pathway=[]
    for i,(title,detail,horizon,confidence) in enumerate(base_path):
        status="complete" if i<current_index else "current" if i==current_index else "next"
        pathway.append({"title":title,"detail":detail,"horizon":horizon,"confidence":confidence,"status":status})

    high=sum(1 for b in blockers if b["severity"]=="High"); med=sum(1 for b in blockers if b["severity"]=="Medium")
    readiness=max(28,min(94,42 + min(18,int(exp*5)) + min(16,len(skills)*2) + (8 if education else 0) + (5 if occupation.lower()!="general professional" else 0) - high*7 - med*3))

    first=blockers[0]
    action_map={
      "occupation":("Resolve your target occupation","Confirm the occupation before optimising jobs or migration options.",24,"Verify occupation"),
      "classification":("Verify your occupation classification",f"Your inferred target is {occupation}, but the classification still needs evidence based verification.",22,"Build evidence plan"),
      "skills":("Make your capabilities visible","Your profile needs more concrete skill evidence before role matching can be trusted.",20,"Build evidence plan"),
      "experience":("Build occupation relevant evidence",f"The biggest gain now is credible experience that proves you can perform {occupation} work.",21,"Build evidence plan"),
      "education":("Confirm qualification alignment","Qualification detail is currently limiting occupation and graduate pathway confidence.",18,"Review evidence"),
      "visa":("Confirm your work rights","Pathway cannot rank immediate actions correctly until your current work rights are known.",25,"Update profile"),
      "visa_timing":("Add your visa timeline","Timing is needed to prioritise career and migration actions in the right order.",16,"Update profile"),
      "jobs_feed":("Strengthen the market signal","Your profile is usable, but live vacancy coverage is the weakest remaining data input.",12,"View evidence plan"),
      "optimisation":("Target the highest value opportunities",f"Your profile is sufficiently complete to focus on roles that strengthen your {occupation} pathway.",14,"View action plan")
    }
    title,why,impact,cta=action_map.get(first["code"],action_map["optimisation"])
    top={"title":title,"why":why,"impact":impact,"cta":cta,"time":"Start now","blockerCode":first["code"]}

    return {"readiness":readiness,"readinessLabel":"Career evidence readiness","topAction":top,"pathway":pathway,"blockers":blockers,"evidencePlan":evidence,"currentStep":current_index,"disclaimer":"Decision support only. Not legal or migration advice."}

