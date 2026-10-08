from skill_reasoning import assess, eligibility, visa_class
from job_analysis import analyse

EVIDENCE = [
    {"source": "Your skills list", "text": "C/C++ | Python | MATLAB"},
    {"source": "Project · Duplex Pump Station PLC and HMI", "text": "TIA Portal, PLCSIM, WinCC HMI simulation. Developed simulated PLC control with duty rotation and alarm acknowledgement."},
    {"source": "Project · Electric Motor Controller", "text": "Developed real-time firmware on ARM Cortex-M4F using FreeRTOS."},
    {"source": "Work · Data Analyst at DHL", "text": "Deployed Power BI dashboard connected to SAP data and pinpointed the root cause of failed deliveries."},
]


def test_direct_transferable_and_gap_with_sources():
    plc = assess("PLC", EVIDENCE, ["plc"])
    assert plc["status"] == "have" and "Pump Station" in plc["source"]
    scada = assess("SCADA", EVIDENCE, ["scada"])
    assert scada["status"] == "transferable" and "WinCC" in scada["reason"]
    emb = assess("Embedded systems", EVIDENCE, ["embedded systems"])
    assert emb["status"] == "transferable" and "Motor Controller" in emb["source"]
    assert assess("Troubleshooting", EVIDENCE, ["troubleshooting"])["status"] == "transferable"
    assert assess("Kubernetes", EVIDENCE, ["kubernetes"])["status"] == "gap"
    # word boundaries: 'excellent' is not Excel
    assert assess("Excel", [{"source": "x", "text": "excellent communicator"}], ["excel"])["status"] == "gap"


def test_eligibility_tiers_by_visa():
    citizen_only = {"category": "citizen_pr", "evidence": "Applicants must be Australian Citizens"}
    assert eligibility(citizen_only, "Temporary Graduate visa (subclass 485)")["tier"] == 2
    assert eligibility(citizen_only, "Australian citizen")["tier"] == 0
    assert eligibility({"category": "work_rights"}, "Temporary Graduate visa (subclass 485)")["tier"] == 0
    assert eligibility({"category": "not_stated"}, "Student visa (subclass 500)")["tier"] == 1
    assert visa_class("Skills in Demand visa (subclass 482)") == "sponsored"


def test_jobs_sorted_eligible_first_with_reasoned_skills():
    def ad(i, text, title="Controls Engineer"):
        return {"title": title, "link": f"https://www.linkedin.com/jobs/view/{2000000+i}/", "companyName": f"Co {i}", "location": "Brisbane, Queensland, Australia", "descriptionText": text}
    items = [ad(1, "Applicants must be Australian Citizens. PLC and SCADA experience required."),
             ad(2, "PLC, SCADA and HMI work on water projects. Troubleshooting skills."),
             ad(3, "Kubernetes and AWS platform engineer.", title="Platform Engineer")]
    out = analyse(items, {"skills": ["Python"], "experienceYears": 1, "visa": "Temporary Graduate visa (subclass 485)", "evidence": EVIDENCE[1:]}, "Controls Engineer")
    order = [r["company"] for r in out["roles"]]
    assert order[0] == "Co 2" and order[-1] == "Co 1"
    first = out["roles"][0]["fit"]
    statuses = {s["skill"]: s["status"] for s in first["skills"]}
    assert statuses["PLC"] == "have" and statuses["SCADA"] == "transferable"
    assert out["roles"][-1]["fit"]["eligibility"]["label"] == "Citizens or PR only"
    assert out["skillStatus"]["PLC"]["status"] == "have"
