from datetime import date

import migration_engine as E
import migration_live as L
from job_analysis import work_rights

TODAY = date(2026, 10, 8)
PROFILE = {"location": "Brisbane, QLD", "visa": "Student visa (subclass 500)", "visaExpiry": "2027-02-28", "occupation": "Mechatronics Engineer",
           "careerFamily": "Mechatronics and automation", "anzsco": "233999", "education": "Bachelor of Engineering (Honours)"}
CIRC = {"dob": "2001-05-14", "qualification": "bachelor", "auQualification": True, "studyState": "QLD", "courseCompletion": "2026-11-20",
        "englishLevel": "proficient", "skillsAssessment": "none", "partner": "single", "regional": "maybe", "employer": "none", "employedInOccupation": "no"}
LIVE_UNPUBLISHED = {"round": {"date": "4 June 2026", "invitations": 10000, "minimumPoints": None, "occupationStatus": "not_published"}}
LIVE_PUBLISHED = {"round": {"date": "4 June 2026", "invitations": 10000, "minimumPoints": 85, "occupationStatus": "published"}}


def plan(circ=None, live=None, profile=None):
    return E.build_plan({**PROFILE, **(profile or {})}, {**CIRC, **(circ or {})}, live if live is not None else LIVE_UNPUBLISHED, TODAY)


def test_points_breakdown_matches_table():
    p = plan()
    rows = {r["id"]: r["points"] for r in p["points"]["rows"]}
    assert rows == {"age": 30, "english": 10, "experience": 0, "qualification": 15, "australianStudy": 5, "specialist": 0,
                    "professionalYear": 0, "naati": 0, "regionalStudy": 0, "partner": 10}
    assert p["points"]["total"] == 70


def test_experience_cap_and_age_band_move_with_time():
    ctx = E.Ctx(PROFILE, {**CIRC, "auExperienceYears": 9, "overseasExperienceYears": 9}, {}, TODAY)
    exp = next(r for r in E.points_at(ctx)["rows"] if r["id"] == "experience")
    assert exp["points"] == 20  # combined cap
    later = E.points_at(ctx, date(2034, 6, 1))  # after 33rd birthday
    assert next(r for r in later["rows"] if r["id"] == "age")["points"] == 25


def test_485_window_and_deadline_use_visa_expiry_when_earlier():
    p = plan()
    deadline = next(d for d in p["deadlines"] if d["title"] == "Last day to lodge the 485")
    assert deadline["date"] == "2027-02-28"  # visa expires before completion + 6 months (2027-05-20)


def test_unpublished_occupation_makes_189_long_shot_and_user_target_gives_dated_scenario():
    p = plan()
    s189 = next(s for s in p["strategies"] if s["id"] == "189")
    assert s189["level"] == "Long shot" and s189["prWindow"]["from"] is None
    p2 = plan({"targetPoints": 80})
    s189b = next(s for s in p2["strategies"] if s["id"] == "189")
    assert s189b["points"]["targetBasis"] == "user" and s189b["points"]["competitiveDate"]


def test_published_minimum_met_is_strong():
    p = plan({"englishLevel": "superior"}, LIVE_PUBLISHED)  # 80 points vs 85
    assert next(s for s in p["strategies"] if s["id"] == "189")["level"] in {"Viable", "Stretch"}
    p = plan({"englishLevel": "superior", "naati": True}, LIVE_PUBLISHED)  # 85
    assert next(s for s in p["strategies"] if s["id"] == "189")["level"] == "Strong"


def test_partner_route_only_with_citizen_partner_and_regional_preference_respected():
    assert not any(s["id"] == "partner" for s in plan()["strategies"])
    p = plan({"partner": "partner_citizen_pr", "partnerRelationship": "married", "regional": "no"})
    assert p["strategies"][0]["id"] == "partner"
    assert next(s for s in p["strategies"] if s["id"].startswith("491"))["level"] == "Not preferred"


def test_age_45_blocks_points_tested_routes():
    p = plan({"dob": "1980-01-01"})
    assert next(s for s in p["strategies"] if s["id"] == "189")["level"] == "Not available"


def test_settled_status_returns_no_strategies():
    p = plan(profile={"visa": "Australian permanent resident"})
    assert p["strategies"] == [] and p["context"]["settled"]


def test_milestones_are_dated_and_ordered():
    for s in plan()["strategies"]:
        starts = [m["start"] for m in s["milestones"]]
        assert starts == sorted(starts)
        assert all(m["end"] >= m["start"] for m in s["milestones"])


def test_employer_status_changes_482_route():
    assert next(s for s in plan()["strategies"] if s["id"] == "482-186")["level"] == "Depends on employer"
    assert next(s for s in plan({"employer": "offer"})["strategies"] if s["id"] == "482-186")["level"] == "Strong"


def test_decision_tree_highlights_answers():
    tree = plan({"partner": "single"})["tree"]
    assert tree["id"] == "partner" and tree["answer"] == "no"


def test_missing_inputs_listed():
    p = E.build_plan(PROFILE, {}, {}, TODAY)
    fields = {m["field"] for m in p["missing"]}
    assert {"dob", "courseCompletion", "englishLevel"} <= fields
    assert p["assumptions"]


def test_live_fee_and_state_parsers():
    html = '<html><body><div>Cost From AUD6,135.00</div></body></html>'
    assert L.parse_fee(html) == 6135
    assert L.parse_fee("<p>No price here</p>") is None
    page = "<main><p>Registrations of Interest for the 2026-27 program are now open for eligible occupations.</p></main>"
    assert "now open" in L.parse_state_status(page)


def test_work_rights_detection():
    assert work_rights("Applicants must be Australian Citizens to meet defence security requirements")["category"] == "citizen_pr"
    assert work_rights("Visa sponsorship is available for the right candidate")["category"] == "sponsorship"
    assert work_rights("We are unable to offer visa sponsorship")["category"] == "no_sponsorship"
    assert work_rights("Great team and free coffee")["category"] == "not_stated"
