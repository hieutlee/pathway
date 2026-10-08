from __future__ import annotations
import io, os, re, time
from datetime import datetime, timezone
from typing import Any, Literal
import httpx
from bs4 import BeautifulSoup
from cachetools import TTLCache
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv
from intelligence import migration_intelligence, shortage_intelligence, profile_checklist
from job_provider import apify_jobs, adzuna_jobs, configuration
from job_search import search_jobs
import asyncio
import migration_rules
from migration_engine import build_plan
from migration_live import gather_live
import resume_parser
import occupations
from pypdf import PdfReader
from docx import Document

load_dotenv(Path(__file__).with_name(".env"))

app = FastAPI(title="Pathway Live Intelligence API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","), allow_methods=["GET","POST"], allow_headers=["Content-Type"])

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
    payload["cached"]=True
    payload["freshness"]=age_label(item["ts"])
    return payload

def cache_put(bucket: str, key: str, payload: dict):
    if payload.get("status") in {"fresh", "partial", "stale"}:
        CACHE[bucket][key]={"payload":payload,"ts":time.time()}
    return payload

async def fetch_html(url: str, timeout=10):
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
        r=await client.get(url)
        r.raise_for_status()
        return r.text

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
            doc=Document(io.BytesIO(raw))
            parts=[p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(dict.fromkeys(c.text.strip() for c in row.cells if c.text.strip())))
            text="\n".join(parts)
        else: text=raw.decode("utf-8",errors="ignore")
    except Exception:
        text=raw.decode("utf-8",errors="ignore")
    if len(text.strip())<80:
        return {"status":"unreadable","note":"Very little text could be read from this file. It may be a scanned image. Try a text-based PDF or DOCX.","resume":None}
    resume=resume_parser.parse(text)
    hints=migration_hints(text)
    best=resume["suggestions"][0] if resume["suggestions"] else None
    return {"status":"parsed","resume":resume,"visa":hints.pop("visa",""),"migrationHints":hints,"occupation":best}

@app.get("/api/occupations")
def occupation_catalogue():
    return {"occupations":occupations.catalogue_payload()}


MONTHS={m:i for i,m in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],1)}

def migration_hints(text:str)->dict:
    """Facts a resume can reveal for migration planning. Every hint is shown for review, never assumed final."""
    lower=text.lower(); hints:dict[str,Any]={}; found=[]
    for name,(state,regional) in sorted(migration_rules.INSTITUTIONS.items(), key=lambda x:-len(x[0])):
        if re.search(rf'(?<![a-z]){re.escape(name)}(?![a-z])',lower):
            hints.update(institution=(name.title().replace(" Of "," of ").replace(" The "," the ") if len(name)>4 else name.upper()), studyState=state, studyRegional="no" if regional in {"check","no"} else "yes", auQualification=True)
            if regional=="check": hints["studyRegionalNote"]="This institution has metropolitan and regional campuses. Confirm your campus."
            found.append("Australian institution")
            break
    if re.search(r'ph\.?d|doctor of philosophy',lower): hints["qualification"]="doctorate"
    elif re.search(r'master of (?:philosophy|research)|mphil|masters? by research',lower): hints["qualification"]="masters_research"
    elif re.search(r'master of|masters? degree|\bmsc\b|\bmba\b|\bmeng\b',lower): hints["qualification"]="masters_coursework"
    elif re.search(r'bachelor|b\.?eng|honours',lower): hints["qualification"]="bachelor"
    elif 'diploma' in lower: hints["qualification"]="diploma"
    comp=re.search(r'(?:expected|anticipated|completion|graduat\w*|grad\.?)\s*(?:date)?\s*:?\s*(?:in\s*)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(20\d{2})',lower) or re.search(r'(?:20\d{2})\s*[-–]\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(20\d{2})',lower)
    if comp and hints.get("auQualification"):
        hints["courseCompletion"]=f"{comp.group(2)}-{MONTHS[comp.group(1)]:02d}-15"; found.append("completion month")
    ielts=re.search(r'ielts[^0-9\n]{0,30}(\d(?:\.5)?)',lower); pte=re.search(r'pte(?: academic)?[^0-9\n]{0,30}(\d{2})',lower)
    if ielts:
        score=float(ielts.group(1)); hints["englishLevel"]="superior" if score>=8 else "proficient" if score>=7 else "competent" if score>=6 else ""
        hints["englishNote"]=f"IELTS {score:g} found. Points depend on every band, so confirm each score."
    elif pte:
        score=int(pte.group(1)); hints["englishLevel"]="superior" if score>=88 else "proficient" if score>=76 else "competent" if score>=54 else ""
        hints["englishNote"]=f"PTE {score} found. Points depend on each communicative skill, so confirm each score."
    degree=re.search(r'(?:bachelor|master|diploma|doctor|graduate certificate|associate degree)[^\n]{0,90}',lower)
    scope=degree.group(0) if degree else lower
    for field,pattern in (("engineering",r'engineering|mechatronic|robotic'),("ict",r'information technology|computer science|computing|software|data science|data analytics|cyber|information systems'),
                          ("accounting",r'accounting|accountancy|finance'),("nursing",r'nursing|midwifery'),("teaching",r'education|teaching'),("trades",r'certificate (?:iii|iv)|trade')):
        if re.search(pattern,scope): hints["fieldOfStudy"]=field; found.append("field of study"); break
    else:
        if degree: hints["fieldOfStudy"]="other"
    if re.search(r'naati|credentialed community language|\bccl\b',lower): hints["naati"]=True
    if re.search(r'professional year',lower): hints["professionalYear"]=True
    if re.search(r'(?:subclass|visa)\s*485|temporary graduate',lower): hints["visa"]="Temporary Graduate visa (subclass 485)"
    elif re.search(r'(?:subclass|visa)\s*500|student visa',lower): hints["visa"]="Student visa (subclass 500)"
    elif re.search(r'permanent resident',lower): hints["visa"]="Australian permanent resident"
    elif re.search(r'australian citizen',lower) and not re.search(r'must be an australian citizen',lower): hints["visa"]="Australian citizen"
    hints["found"]=found
    return hints

@app.get("/api/intelligence/migration")
async def migration(occupation: str=Query(""), state: str=Query("QLD"), anzsco: str=Query(""), visa: str=Query(""), experienceYears: float=Query(0), education: str=Query("")):
    key=(occupation, state, anzsco)
    payload=cache_get("migration",key)
    if payload is None:
        payload=cache_put("migration",key,await migration_intelligence(occupation,state,anzsco))
    return enrich_migration(payload,occupation,visa,experienceYears,education,state)

def enrich_migration(payload:dict, occupation:str, visa:str="", experience_years:float=0, education:str="", state:str="QLD"):
    p=dict(payload); p["latestRound"]=dict(payload.get("latestRound",{}))
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
async def occupation(occupation: str=Query(""), state: str=Query("QLD"), anzsco: str=Query(""), osca: str=Query("")):
    key=(occupation,state,anzsco,osca)
    if cached:=cache_get("occupation",key): return cached
    return cache_put("occupation",key,await shortage_intelligence(occupation,state,anzsco,osca))

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
        trend=[]
        payload={"status":"fresh","freshness":"Source checked just now","updated":"just now","checkedAt":now_iso(),"source":"Jobs and Skills Australia Internet Vacancy Index","sourceUrl":JSA_IVI,
                 "headline":released.group(1) if released else "Release not extracted",
                 "subheadline":f"Released {released.group(2)}" if released else "Monthly online vacancy intelligence",
                 "releasePeriod":released.group(1) if released else None,"releaseDate":released.group(2) if released else None,
                 "nextReleasePeriod":next_release[0] if next_release else None,"nextReleaseDate":next_release[1] if next_release else None,
                 "downloadSeries":download_count or None,"coverage":"Online job advertisements across occupations, states and regions",
                 "trend":trend,"trendMode":"unavailable","note":"Occupation vacancy time series is not connected. No illustrative values are shown."}
        if not released:
            payload.update(status="partial", freshness="Release metadata unavailable")
        return cache_put("vacancies",key,payload)
    except Exception as e:
        return {"status":"unavailable","freshness":"Live check failed","updated":"not updated","source":"JSA Internet Vacancy Index","sourceUrl":JSA_IVI,"headline":"Unavailable","subheadline":"Live vacancy source could not be reached","trend":[],"error":type(e).__name__}

@app.get("/api/intelligence/jobs")
async def jobs(occupation: str=Query(""), state: str=Query("QLD"), anzsco: str=Query(""), skills: str=Query(""), education: str=Query(""), goal: str=Query(""), candidates: str=Query("")):
    search_roles=list(dict.fromkeys(([occupation] if occupation else [])+[role.strip() for role in candidates.split("|") if role.strip()]))[:8]
    skill_list=[skill.strip() for skill in skills.split(",") if skill.strip()]
    config=configuration()
    provider="apify" if any(config.values()) or not (os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY")) else "adzuna"
    key=(occupation,state,skills,candidates,provider,config["task"],config["dataset"],bool(config["token"]))
    if cached:=cache_get("jobs",key): return cached
    payload=await (apify_jobs(search_roles,state,skill_list) if provider=="apify" else adzuna_jobs(search_roles,state,skill_list))
    return cache_put("jobs",key,payload)

class RecommendationRequest(BaseModel):
    profile: dict[str,Any]
    intelligence: dict[str,Any]

class EvidenceItem(BaseModel):
    source: str = Field(default="", max_length=160)
    text: str = Field(default="", max_length=2500)

class JobProfile(BaseModel):
    occupation: str = Field(default="", max_length=160)
    skills: list[str] = Field(default_factory=list, max_length=150)
    experienceYears: float | None = Field(default=None, ge=0, le=80)
    visa: str = Field(default="", max_length=160)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=80)

class JobSearchRequest(BaseModel):
    role: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=160)
    dateWindow: Literal["anyTime", "past24Hours", "pastWeek", "pastMonth"] = "anyTime"
    profile: JobProfile = Field(default_factory=JobProfile)
    startIfMissing: bool = True

@app.post("/api/jobs/search")
async def job_search(req: JobSearchRequest):
    return await search_jobs(req.role, req.location, req.profile.model_dump(), req.dateWindow, req.startIfMissing)

class MigrationPlanRequest(BaseModel):
    profile: dict[str,Any]
    circumstances: dict[str,Any] = Field(default_factory=dict)
    jobs: dict[str,Any] | None = None

async def _cached_source(bucket, key, factory, timeout):
    if cached:=cache_get(bucket,key): return cached
    try:
        return cache_put(bucket,key,await asyncio.wait_for(factory(),timeout))
    except Exception as exc:
        return {"status":"unavailable","error":type(exc).__name__}

@app.post("/api/migration/plan")
async def migration_plan(req: MigrationPlanRequest):
    p=req.profile or {}
    occupation=p.get("occupation") or ""; anzsco=p.get("anzsco") or ""; state=(p.get("location") or "QLD").split(",")[-1].strip() or "QLD"
    round_payload, shortage_payload, extra = await asyncio.gather(
        _cached_source("migration",(occupation,state,anzsco),lambda: migration_intelligence(occupation,state,anzsco),25),
        _cached_source("occupation",(occupation,state,anzsco,p.get("osca") or ""),lambda: shortage_intelligence(occupation,state,anzsco,p.get("osca") or ""),25),
        asyncio.wait_for(gather_live(),15))
    live={"round":(round_payload.get("latestRound") or {}) if round_payload.get("status") in {"fresh","partial","stale"} else {},
          "shortage":shortage_payload.get("occupationResult") or {},
          "fees":extra["fees"],"states":extra["states"],"jobs":req.jobs}
    plan=build_plan(p,req.circumstances,live)
    plan["liveSources"]=[
        {"id":"round","label":"SkillSelect invitation round","status":round_payload.get("status","unavailable"),"checkedAt":round_payload.get("checkedAt"),"sourceUrl":round_payload.get("sourceUrl") or HOME_AFFAIRS,
         "detail":(f"{live['round'].get('date')} · {live['round'].get('invitations'):,} invitations" if live['round'].get('date') and live['round'].get('invitations') is not None else round_payload.get("note") or "Unavailable")},
        {"id":"shortage","label":"JSA shortage ratings by state","status":shortage_payload.get("status","unavailable"),"checkedAt":shortage_payload.get("checkedAt"),"sourceUrl":shortage_payload.get("downloadUrl") or shortage_payload.get("sourceUrl"),
         "detail":(f"{live['shortage'].get('occupation')} · {shortage_payload.get('oslYear')} list" if live['shortage'] else shortage_payload.get("shortageNote") or "Unavailable")},
        {"id":"fees","label":"Visa charges on Home Affairs pages","status":"fresh" if extra["fees"] else "fallback","checkedAt":extra["report"]["checkedAt"],"sourceUrl":migration_rules.PRICING_URL,
         "detail":(f"Live for {', '.join(extra['report']['feesLive'])}" if extra["fees"] else f"Rulebook values from 1 July 2026, verified {migration_rules.RULEBOOK_VERIFIED}")},
        {"id":"states","label":"State program notices","status":"fresh" if extra["states"] else "fallback","checkedAt":extra["report"]["checkedAt"],"sourceUrl":migration_rules.STATES["QLD"]["url"],
         "detail":(f"Live excerpts for {', '.join(extra['report']['statesLive'])}" if extra["states"] else f"Rulebook status, verified {migration_rules.STATE_STATUS_VERIFIED}")},
        {"id":"jobs","label":"Work rights in collected adverts","status":"fresh" if (req.jobs or {}).get("count") else "unavailable","checkedAt":(req.jobs or {}).get("collectedAt"),"sourceUrl":None,
         "detail":(f"{req.jobs.get('count')} adverts for {req.jobs.get('role')}" if (req.jobs or {}).get("count") else "Run a Jobs search to add employer evidence")},
    ]
    return plan

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
        add_blocker("jobs_feed","Live vacancy coverage is limited", jobs.get("note") or "Current advertised vacancies could not be verified from the connected job provider.", "Low")

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
    top={"title":title,"why":why,"cta":cta,"time":"Start now","blockerCode":first["code"]}

    return {"profileCompleteness":profile_checklist(p),"topAction":top,"pathway":pathway,"blockers":blockers,"evidencePlan":evidence,"currentStep":current_index,"disclaimer":"Decision support only. Not legal or migration advice."}

