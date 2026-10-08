from datetime import date

import resume_parser as P

TODAY = date(2026, 10, 8)

# Fictional resume in the common two-column PDF layout (company and location glued, dates glued to titles).
PDF_STYLE = """Minh Anh Tran
0412 345 678|minh.tran@example.com |linkedin.com/in/minhtran
Summary
Graduate Mechatronics Engineer from Queensland University of Technology focused on PLC programming and embedded control.
Selected as a finalist in the 2025 Engineering Showcase.
Education
Queensland University of TechnologyBrisbane City
Bachelor of Engineering (Honours), Mechatronics EngineeringFeb 2021 – Nov 2025
• Capstone selected for the 2025 Engineering Showcase, 1 of 25 university-wide
Kelvin Grove State CollegeBrisbane, QLD
Queensland Certificate of EducationFeb 2017 – Nov 2018
Technical Skills
Languages: C/C++, Python, Structured Text
Automation: Siemens TIA Portal, Rockwell Studio 5000
Experience
Acme Automation Brisbane City
Graduate Controls Engineer Jan 2026 – Present
• Commissioned PLC and HMI upgrades for water treatment plants built to AS 4254.2-2012 and IEC 61131-3.
• Wrote ladder logic and structured text for pump stations, reducing nuisance alarms by 30%
across three sites.
Coles Group Brisbane City
Retail Team Member Mar 2019 – Dec 2021
• Served customers and managed stock rotation.
QUT Racing Brisbane City
Volunteer Electrical Lead Aug 2023 – Nov 2023
• Designed the low voltage harness.
Projects
Pump Station PLC|TIA Portal, PLCSIM
• Duty and standby rotation with fault recovery.
Line Follower Robot|C, FreeRTOS
• PID steering on an ARM Cortex-M4.
Volunteering
Red Cross Brisbane City
Event Volunteer 2018 – 2019
• Helped at blood drives.
"""

# Fictional one-line-per-role layout from a DOCX export.
DOCX_STYLE = """Priya Sharma
priya@example.com
WORK EXPERIENCE
Data Analyst at Telstra, Melbourne | 03/2023 - Present
- Built Power BI dashboards on SQL data.
Junior Analyst at Infosys, Bangalore | 06/2020 - 02/2023
- Automated reporting in Python.
EDUCATION
Master of Data Science, Monash University | 2021 - 2022
Bachelor of Technology in Computer Science, Anna University | 2016 - 2020
"""


def test_experience_durations_come_only_from_role_dates():
    r = P.parse(PDF_STYLE, TODAY)
    roles = {e["org"]: e for e in r["experience"]}
    assert set(roles) == {"Acme Automation", "Coles Group"}
    assert roles["Acme Automation"]["current"] and roles["Acme Automation"]["months"] == 9
    assert roles["Coles Group"]["months"] == 34
    # standards years and school dates never inflate experience
    assert all(e["months"] < 40 for e in r["experience"])
    totals = P.summarise_experience(r["experience"], [True, False], TODAY, date(2025, 11, 1))
    assert totals["paidMonths"] == 43 and totals["relevantMonths"] == 9


def test_volunteering_is_separated_even_inside_experience():
    r = P.parse(PDF_STYLE, TODAY)
    vols = {v["org"] for v in r["volunteering"]}
    assert vols == {"QUT Racing", "Red Cross"}
    assert all(not e["volunteer"] for e in r["experience"])


def test_education_major_level_and_glued_columns():
    r = P.parse(PDF_STYLE, TODAY)
    uni, school = r["education"]
    assert uni["degree"] == "Bachelor of Engineering (Honours)" and uni["major"] == "Mechatronics Engineering"
    assert uni["institution"] == "Queensland University of Technology" and uni["australian"] and uni["level"] == "bachelor"
    assert uni["end"] == "2025-11-01"
    assert school["level"] == "secondary"


def test_projects_skills_achievements_and_wrapped_bullets():
    r = P.parse(PDF_STYLE, TODAY)
    assert [p["name"] for p in r["projects"]] == ["Pump Station PLC", "Line Follower Robot"]
    assert r["projects"][0]["tools"] == ["TIA Portal", "PLCSIM"]
    acme = r["experience"][0]
    assert acme["bullets"][1].endswith("across three sites.")
    assert {g["name"] for g in r["skillGroups"]} == {"Languages", "Automation"}
    assert any("1 of 25" in a["text"] for a in r["achievements"])


def test_occupation_suggestion_follows_degree_and_summary_not_keywords():
    r = P.parse(PDF_STYLE, TODAY)
    assert r["suggestions"][0]["title"] == "Mechatronics Engineer" and r["suggestions"][0]["anzsco"] == "233999"
    assert r["location"] == "Brisbane, QLD"
    assert r["experience"][0]["relevant"] and not r["experience"][1]["relevant"]


def test_one_line_role_layout():
    r = P.parse(DOCX_STYLE, TODAY)
    titles = [(e["title"], e["org"], e["where"]) for e in r["experience"]]
    assert titles[0][0] == "Data Analyst" and "Telstra" in titles[0][1]
    assert r["experience"][1]["where"] == "overseas"
    assert r["education"][0]["level"] == "masters_coursework"
    assert r["suggestions"][0]["field"] == "ict"


def test_skills_inferred_when_no_skills_section():
    text = PDF_STYLE.split("Technical Skills")[0] + "Experience" + PDF_STYLE.split("Experience",1)[1]
    r = P.parse(text, TODAY)
    inferred = [g for g in r["skillGroups"] if g.get("inferred")]
    assert inferred and "PLC" in inferred[0]["items"]
    assert any("concluded" in w for w in r["warnings"])
