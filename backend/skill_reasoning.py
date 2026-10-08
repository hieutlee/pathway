"""Explainable skill reasoning between a job advert and a candidate's own evidence.

For each skill an advert mentions, the candidate's resume evidence (work, projects,
volunteering, education, listed skills) is checked in two steps:

1. Direct: the skill itself (or an alias of it) appears in the candidate's evidence.
2. Transferable: related work appears that builds the same capability, for example
   writing logic in TIA Portal builds PLC programming. Each relation carries a plain
   reason so the interface can say why, with the source it came from.

Nothing is inferred without a quoted source. This is deliberately a curated, auditable
map rather than a black box: extend RELATIONS when a new pattern is needed.
"""
from __future__ import annotations

import re

# advert skill label -> list of (evidence terms, why it transfers)
RELATIONS: dict[str, list[tuple[list[str], str]]] = {
    "PLC": [(["ladder logic", "structured text", "function block", "tia portal", "studio 5000", "logix", "plcsim", "codesys", "step 7", "s7-1200", "s7-1500", "iec 61131"], "PLC programming software and IEC 61131 languages")],
    "SCADA": [(["ignition", "wincc", "factorytalk view", "citect", "modbus", "opc ua", "opc-ua", "historian"], "SCADA platforms and industrial protocols"),
              (["hmi", "operator screens", "alarm"], "operator interfaces, alarms and trending")],
    "HMI": [(["wincc", "factorytalk view", "operator screen", "touchscreen", "ignition", "scada"], "building operator screens")],
    "Control systems": [(["pid", "lqr", "lqi", "model predictive", "mpc", "kalman", "state estimation", "simulink", "closed-loop", "closed loop", "feedback control", "motor control", "control logic"], "control design and tuning")],
    "Embedded systems": [(["firmware", "rtos", "freertos", "microcontroller", "mcu", "arm cortex", "stm32", "esp32", "tm4c", "interrupt", "isr", "jetson"], "firmware on microcontrollers")],
    "Commissioning": [(["site acceptance", "factory acceptance", "test matrix", "retest", "start-up", "bring-up", "verified", "verification"], "testing and verifying systems before handover")],
    "Teamwork": [(["cross-functional", "collaborat", "team", "motorsport", "group", "volunteer"], "working in teams")],
    "Problem solving": [(["root cause", "optimi", "resolved", "pinpoint", "fault", "speedup"], "solving technical problems")],
    "Documentation": [(["documented", "documentation", "functional description", "technical report", "reports", "input/output schedule"], "technical documentation")],
    "Agile": [(["sprint", "scrum", "kanban", "iterative", "ci/cd"], "iterative delivery practices")],
    "Linux": [(["fedora", "ubuntu", "bash", "linux"], "Linux environments")],
    "CUDA": [(["gpu", "parallel", "kernel"], "GPU programming")],
    "Troubleshooting": [(["fault", "debug", "root cause", "defect", "diagnos", "ict support", "investigat", "resolved"], "finding and fixing faults")],
    "Functional safety": [(["interlock", "shutdown circuit", "safety", "permissive", "over-voltage", "over-current", "e-stop", "emergency stop"], "safety interlocks and protective logic")],
    "Robotics": [(["robot", "kinematics", "ros", "autonomous", "mobile base", "manipulator"], "robotic systems")],
    "Machine vision": [(["computer vision", "opencv", "camera", "image processing", "yolo"], "vision-based perception")],
    "Machine learning": [(["pytorch", "tensorflow", "neural", "deep learning", "model training", "scikit", "rapids"], "building and training models")],
    "AI tools": [(["pytorch", "tensorflow", "cuda", "machine learning", "deep learning", "llm", "copilot", "chatgpt"], "hands-on AI and ML tooling")],
    "Python": [(["python", "jupyter", "pandas", "numpy"], "Python programming")],
    "C++": [(["c/c++", "c++", "cuda c", "cmake"], "C and C++ development"), (["firmware", "embedded c", " c,", "freertos"], "low-level C programming that transfers to C++")],
    "C#": [(["c++", "java", "object-oriented"], "object-oriented programming in a similar language")],
    "Java": [(["c++", "c#", "object-oriented"], "object-oriented programming in a similar language")],
    "Git": [(["git", "github", "gitlab", "version control", "ci/cd"], "version control workflows")],
    "Docker": [(["docker", "container"], "containerised development")],
    "Kubernetes": [(["docker", "container"], "containers, the building block Kubernetes orchestrates")],
    "AWS": [(["cloud computing", "azure", "gcp", "docker"], "cloud and deployment fundamentals")],
    "Azure": [(["cloud computing", "aws", "gcp", "docker"], "cloud and deployment fundamentals")],
    "SQL": [(["sql", "database", "sap data", "query"], "querying structured data")],
    "Power BI": [(["power bi", "tableau", "dashboard"], "building dashboards and reports")],
    "Tableau": [(["power bi", "dashboard"], "BI dashboards in a comparable tool")],
    "Excel": [(["excel", "spreadsheet", "power bi", "data entry"], "spreadsheet and reporting work")],
    "SAP": [(["sap", "erp"], "working with ERP data")],
    "CAD": [(["solidworks", "autocad", "fusion 360", "creo", "inventor", "catia", "revit", "3d model", "modeling", "modelling", "dfm"], "computer-aided design")],
    "SolidWorks": [(["fusion 360", "creo", "inventor", "catia", "cad", "dfm"], "parametric CAD in a comparable tool")],
    "AutoCAD": [(["solidworks", "revit", "cad", "drafting", "floor plan", "dfm"], "drafting and CAD")],
    "MATLAB": [(["simulink", "matlab"], "MATLAB-based analysis and simulation")],
    "Simulink": [(["matlab", "simulation", "control design"], "model-based simulation")],
    "Allen Bradley": [(["studio 5000", "rockwell", "logix", "factorytalk"], "Rockwell software, which is the Allen-Bradley platform")],
    "Siemens TIA Portal": [(["tia portal", "step 7", "wincc", "plcsim"], "the Siemens TIA toolchain")],
    "PCB design": [(["pcb", "altium", "kicad", "eagle", "schematic"], "board-level electronics design")],
    "Altium": [(["kicad", "eagle", "pcb"], "PCB design in a comparable tool")],
    "ROS": [(["ros", "robot operating system", "gazebo"], "robotics middleware")],
    "Project management": [(["schedule", "coordinat", "timeline", "milestone", "delivered", "capstone", "managed"], "planning and delivering work to a deadline")],
    "Stakeholder management": [(["client", "stakeholder", "escalat", "dealership", "customer", "coordinators", "senior engineers"], "working with clients and senior staff")],
    "Communication": [(["report", "documented", "documentation", "presented", "technical paper", "wrote", "functional description"], "clear technical writing and reporting")],
    "Quality assurance": [(["test matrix", "unit testing", "validation", "audit", "standards", "compliance", "as 4254", "iso "], "testing against standards")],
    "Risk assessment": [(["hazard", "risk", "safety", "fault"], "identifying risks and failure modes")],
    "Customer service": [(["customer", "dealership", "hospitality", "support", "retail"], "customer-facing work")],
    "Teaching": [(["tutor", "mentor", "teaching assistant", "demonstrator"], "teaching or mentoring")],
}

ALIASES = {"C++": ["c/c++", "c++"], "PLC": ["plc"], "Embedded systems": ["embedded"], "Control systems": ["control systems", "control system"],
           "Machine learning": ["machine learning"], "AI tools": ["artificial intelligence", "ai tools", "generative ai"], "Git": ["git"],
           "Allen Bradley": ["allen bradley", "allen-bradley"], "Siemens TIA Portal": ["tia portal"], "Power BI": ["power bi"], "SQL": ["sql"]}


STEMS = {"coordinat", "escalat", "diagnos", "investigat", "modell", "deliver"}


def _find(term, text):
    t = term.strip().lower()
    if not t:
        return None
    pattern = (r"(?<![a-z0-9])" if t[0].isalnum() else "") + re.escape(t)
    if t[-1].isalnum() and t not in STEMS:
        pattern += r"(?![a-z0-9])"
    return re.search(pattern, text, re.I)


def _snip(text, m, radius=70):
    s, e = max(0, m.start() - radius), min(len(text), m.end() + radius)
    return ("…" if s else "") + text[s:e].strip() + ("…" if e < len(text) else "")


def assess(skill: str, evidence: list[dict], aliases_for_skill: list[str]) -> dict:
    """Return have / transferable / gap for one advertised skill, with the reason and its source."""
    terms = list(dict.fromkeys([skill.lower()] + [a.lower() for a in ALIASES.get(skill, [])] + [a.lower() for a in aliases_for_skill]))
    for item in evidence:
        text = item.get("text", "")
        for term in terms:
            m = _find(term, text)
            if m:
                where = item.get("source", "Your resume")
                return {"skill": skill, "status": "have", "source": where,
                        "reason": f"{where} mentions {m.group(0).strip()}.", "quote": _snip(text, m)}
    for related, why in RELATIONS.get(skill, []):
        for term in related:  # strongest terms first
            for item in evidence:
                text = item.get("text", "")
                m = _find(term, text)
                if m:
                    where = item.get("source", "Your resume")
                    return {"skill": skill, "status": "transferable", "source": where,
                            "reason": f"Transferable: {where} shows {m.group(0).strip()}, which builds {why}.", "quote": _snip(text, m)}
    return {"skill": skill, "status": "gap", "source": "", "reason": f"No direct or related evidence of {skill} found in your resume.", "quote": ""}


VISA_CLASS = [
    ("citizen_pr", r"australian citizen|permanent resident|subclass (?:189|190|191|186|858|801|100)"),
    ("student", r"subclass 500|student visa|subclass 590"),
    ("sponsored", r"subclass 482|subclass 494|subclass 457|subclass 407"),
    ("offshore", r"offshore|no current australian visa"),
    ("temporary", r"subclass 485|temporary graduate|subclass 417|subclass 462|subclass 491|subclass 820|subclass 309|bridging"),
]


def visa_class(visa: str) -> str:
    v = (visa or "").lower()
    return next((k for k, p in VISA_CLASS if re.search(p, v)), "unknown")


def eligibility(work_rights: dict, visa: str) -> dict:
    """Tier 0 = can apply, 1 = check, 2 = not eligible on the current visa."""
    cls = visa_class(visa)
    cat = (work_rights or {}).get("category", "not_stated")
    ev = (work_rights or {}).get("evidence", "")
    if cls == "citizen_pr":
        return {"tier": 0, "label": "Eligible", "reason": "Your status meets citizenship or PR requirements.", "evidence": ev, "category": cat}
    if cat == "citizen_pr":
        return {"tier": 2, "label": "Citizens or PR only", "reason": "This advert asks for Australian citizenship or permanent residence, which a temporary visa does not meet.", "evidence": ev, "category": cat}
    if cat == "clearance":
        return {"tier": 2, "label": "Security clearance", "reason": "Australian security clearances generally require citizenship, so this role is usually closed to temporary visa holders.", "evidence": ev, "category": cat}
    if cls == "offshore":
        return {"tier": 1, "label": "Needs a visa", "reason": "You would need a visa with work rights or employer sponsorship before starting.", "evidence": ev, "category": cat}
    if cls == "sponsored":
        if cat == "sponsorship":
            return {"tier": 0, "label": "Sponsorship mentioned", "reason": "The advert mentions sponsorship, which a sponsored visa holder needs to change employer.", "evidence": ev, "category": cat}
        return {"tier": 1, "label": "Needs a new nomination", "reason": "Your visa ties you to your sponsor; this employer would need to nominate you.", "evidence": ev, "category": cat}
    if cls == "student":
        if cat == "no_sponsorship":
            return {"tier": 1, "label": "No sponsorship", "reason": "Fine while you have work rights, but this employer says it will not sponsor later. Student visas limit work to 48 hours a fortnight during the course.", "evidence": ev, "category": cat}
        return {"tier": 1, "label": "Check hours", "reason": "Student visas allow 48 hours a fortnight during the course and unlimited hours in breaks. Full-time roles usually suit graduates or after course completion.", "evidence": ev, "category": cat}
    if cat == "no_sponsorship":
        return {"tier": 0, "label": "No sponsorship later", "reason": "You can apply with your current work rights, but this employer will not sponsor you for a future visa.", "evidence": ev, "category": cat}
    if cat == "sponsorship":
        return {"tier": 0, "label": "Sponsorship mentioned", "reason": "You can apply now, and the employer mentions sponsorship, which helps the employer-sponsored PR route.", "evidence": ev, "category": cat}
    if cat == "work_rights":
        return {"tier": 0, "label": "Work rights required", "reason": "Your current visa provides work rights. Have your VEVO record ready.", "evidence": ev, "category": cat}
    return {"tier": 0, "label": "No restriction stated", "reason": "The advert does not state a citizenship, clearance or work-rights restriction.", "evidence": ev, "category": cat}
