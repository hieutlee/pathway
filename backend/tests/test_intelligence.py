import html
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import intelligence as facts
import job_provider as provider
import main


def round_page(total="10,000", old=False, dual=False):
    """Synthetic publisher layout; values are test data, not a bundled live fallback."""
    blocks = '<h3>Invitations issued on 4 June 2026</h3><table><tr><th>Visa subclass</th><th>Total EOIs Invited</th><th>Tie break</th></tr>'
    blocks += f'<tr><td>Skilled Independent visa (subclass 189)</td><td>{total}</td><td>24/04/2026</td></tr></table>'
    blocks += '<h3>Invitations issued by occupation</h3><table>'
    blocks += '<tr><th>Occupation</th><th>Subclass 491</th><th>Subclass 189</th></tr><tr><td>Test Engineer</td><td>65</td><td>95</td></tr>' if dual else '<tr><th>Occupation*</th></tr><tr><td>Test Engineer</td><td>95</td></tr><tr><td>Another Engineer</td><td>N/A</td></tr>'
    blocks += '</table><h3>Total invitations issued during program year</h3><table><tr><td>Skilled Independent visa (subclass 189)</td><td>999999</td></tr></table>'
    if old:
        blocks += '<h3>Invitations issued on 1 July 2025</h3><table><tr><th>Occupation</th></tr><tr><td>Older Engineer</td><td>65</td></tr></table>'
    schema = json.dumps({"content": [{"text": "Current round", "block": blocks}]})
    return f'<input type="hidden" id="ctl00_PageSchemaHiddenField_Input" value="{html.escape(schema, quote=True)}">'


def workbook_bytes():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ANZSCO 2022"
    sheet.append(["Occupation Shortage List"])
    sheet.append(["ANZSCO code", "ANZSCO occupation title", "National", "NSW", "QLD", "SA", "TAS", "WA"])
    sheet.append([233999, "Engineering Professionals nec", "NS", "S", "R", "M", "NS", "S"])
    sheet.append([233914, "Engineering Technologist", "S", "NS", "S", "NS", "NS", "S"])
    osca = workbook.create_sheet("OSCA 2024")
    osca.append(["OSCA code", "OSCA title", "National", "Queensland", "South Australia", "Tasmania"])
    osca.append([243999, "Example Mechatronics Occupation", "S", "NS", "M", "R"])
    raw = io.BytesIO()
    workbook.save(raw)
    return raw.getvalue()


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    for key in ["APIFY_TOKEN", "APIFY_TASK_ID", "APIFY_DATASET_ID", "APIFY_MAX_ITEMS", "APIFY_FIELD_MAP", "APIFY_JOBS_STATE", "ADZUNA_APP_ID", "ADZUNA_APP_KEY"]:
        monkeypatch.delenv(key, raising=False)
    for cache in main.CACHE.values():
        cache.clear()
    facts._source_cache.clear()
    facts._locks.clear()


def test_hidden_schema_is_decoded_and_program_totals_not_confused():
    result = facts.parse_round(round_page(old=True))
    assert result["latestRound"] == {"date": "4 June 2026", "invitations": 10000, "tieBreak": "24/04/2026"}
    assert result["occupationRows"][0]["minimumPoints"] == 95
    assert len(result["occupationRows"]) == 2
    assert result["occupationRows"][1]["minimumPoints"] is None


def test_separate_491_column_never_used_as_189():
    assert facts.parse_round(round_page(dual=True))["occupationRows"][0]["minimumPoints"] == 95


def test_zero_is_real_data():
    assert facts.parse_round(round_page(total="0"))["latestRound"]["invitations"] == 0


def test_blank_home_affairs_page_is_failure():
    with pytest.raises(ValueError):
        facts.parse_round('<h2>Invitation rounds</h2>Current round published')


def test_workbook_ratings_namespaces_and_state_boundaries():
    rows = facts.parse_osl(workbook_bytes())
    result = facts.match_osl(rows, "Mechatronics Engineer", "QLD", anzsco="233999")
    assert result["occupation"] == "Engineering Professionals nec"
    assert result["nationalRating"] == "No shortage"
    assert result["stateRating"] == "Regional shortage"
    assert result["stateRatings"]["SA"] == "Metropolitan shortage"
    assert result["stateRatings"]["TAS"] == "No shortage"
    osca = facts.match_osl(rows, "", "Queensland", osca="243999")
    assert osca["classification"] == "OSCA"
    assert osca["stateRating"] == "No shortage"
    assert facts.match_osl(rows, "Engineer", "QLD") is None
    assert facts.match_osl(rows, "", "QLD", anzsco="243999") is None


def test_latest_workbook_discovery_excludes_unit_groups():
    html = '<a href="/files/2024_occupation_shortage_list.xlsx">2024</a><a href="/files/2025_occupation_shortage_list_6_digit.xlsx">Download</a><a href="/files/2026_unit_group_occupation_shortage_list.xlsx">4 digit unit group</a>'
    assert facts.discover_osl(html)[0] == 2025


@pytest.mark.asyncio
async def test_occupation_cache_includes_state_and_code(monkeypatch):
    async def dataset(kind):
        return {"records": facts.parse_osl(workbook_bytes()), "oslYear": 2025, "downloadUrl": "https://www.jobsandskills.gov.au/example.xlsx", "checkedAt": facts.now_iso()}
    monkeypatch.setattr(facts, "official_dataset", dataset)
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        qld = (await client.get('/api/intelligence/occupation', params={"occupation": "Mechatronics Engineer", "anzsco": "233999", "state": "QLD"})).json()
        nsw = (await client.get('/api/intelligence/occupation', params={"occupation": "Mechatronics Engineer", "anzsco": "233999", "state": "NSW"})).json()
    assert qld["occupationResult"]["stateRating"] == "Regional shortage"
    assert nsw["occupationResult"]["stateRating"] == "Shortage"
    assert qld["occupationMatch"] is False


@pytest.mark.asyncio
async def test_no_occupation_score_is_distinct_from_source_failure(monkeypatch):
    async def dataset(kind):
        return {**facts.parse_round(round_page()), "checkedAt": facts.now_iso()}
    monkeypatch.setattr(facts, "official_dataset", dataset)
    result = await facts.migration_intelligence("Absent Engineer", "QLD")
    assert result["status"] == "fresh"
    assert result["latestRound"]["minimumPoints"] is None
    assert result["latestRound"]["occupationStatus"] == "not_published"
    assert "does not establish" in result["occupationNote"]


@pytest.mark.asyncio
async def test_failed_workbook_is_not_a_negative_shortage_rating(monkeypatch):
    async def failure(kind):
        raise ValueError("bad workbook")
    monkeypatch.setattr(facts, "official_dataset", failure)
    result = await facts.shortage_intelligence("Test Engineer", "QLD")
    assert result["status"] == "unavailable"
    assert result["occupationMatch"] is None


def test_profile_count_is_explainable_and_zero_experience_is_supplied():
    profile = {"occupation": "Test Engineer", "anzsco": "233999", "location": "Brisbane", "education": "BEng", "experienceYears": 0, "skills": ["C++"], "visa": "Temporary Graduate visa (subclass 485)", "visaExpiry": ""}
    result = facts.profile_checklist(profile)
    assert result["completed"] == 7 and result["total"] == 8
    assert not result["checks"][-1]["present"]
    profile["visa"] = "Australian citizen"
    assert facts.profile_checklist(profile)["total"] == 7
    response = main.recommend(main.RecommendationRequest(profile=profile, intelligence={}))
    assert "readiness" not in response
    assert "impact" not in response["topAction"]


def test_cache_preserves_partial_and_failure_states():
    main.cache_put("jobs", "partial", {"status": "partial", "count": None})
    assert main.cache_get("jobs", "partial")["status"] == "partial"
    main.cache_put("jobs", "failure", {"status": "unavailable"})
    assert main.cache_get("jobs", "failure") is None


def job(**changes):
    return {"jobTitle": "Graduate Mechatronics Engineer", "companyName": "Example Engineering", "location": "Brisbane, QLD", "jobUrl": "https://jobs.example.org/123", "description": "<p>Experience with C++ and Python.</p>", **changes}


def test_job_matching_uses_title_location_and_visible_skills():
    items = [job(), job(jobUrl="https://jobs.example.org/123?tracking=x"), job(companyName="Sydney Co", location="Sydney, NSW"), job(jobTitle="Accountant"), job(jobUrl="javascript:alert(1)"), job(isExpired=True)]
    result = provider.rank_jobs(items, ["Mechatronics Engineer"], "QLD", ["C++", "Python", "PLC"])
    assert len(result) == 1
    assert result[0]["matchedSkills"] == ["C++", "Python"]
    assert "match" not in result[0]
    assert "description" not in result[0]


def test_custom_actor_fields_and_unknown_location():
    item = {"position": {"name": "Mechatronics Engineer"}, "application": "https://jobs.example.org/123"}
    mapping = {"title": "position.name", "url": "application"}
    assert provider.rank_jobs([item], ["Mechatronics Engineer"], "QLD", [], mapping) == []
    result = provider.rank_jobs([item], ["Mechatronics Engineer"], "QLD", [], mapping, "QLD")
    assert len(result) == 1
    assert "provider search scope" in result[0]["location"]


@pytest.mark.asyncio
async def test_unconfigured_provider_never_fabricates_listings():
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", [])
    assert result["status"] == "not_configured"
    assert result["roles"] == [] and result["count"] is None


def mock_apify(monkeypatch, age_hours=1, items=None, error=None, dataset_only=False):
    monkeypatch.setenv("APIFY_TOKEN", "test-secret")
    monkeypatch.setenv("APIFY_DATASET_ID" if dataset_only else "APIFY_TASK_ID", "test-id")
    collected = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    records = [job()] if items is None else items
    requests = []
    def handle(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert "test-secret" not in str(request.url)
        if error:
            return httpx.Response(error, json={"error": {"message": "test-secret must never be reflected"}})
        if request.url.path.endswith('/runs/last'):
            assert request.url.params["status"] == "SUCCEEDED"
            return httpx.Response(200, json={"data": {"status": "SUCCEEDED", "defaultDatasetId": "dataset", "finishedAt": collected}})
        if request.url.path.endswith('/items'):
            offset = int(request.url.params["offset"])
            limit = int(request.url.params["limit"])
            return httpx.Response(200, json=records[offset:offset+limit])
        return httpx.Response(200, json={"data": {"itemCount": len(records), "modifiedAt": facts.now_iso()}})
    original_client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs))
    return requests


@pytest.mark.asyncio
async def test_apify_reads_successful_run_with_auth_and_real_counts(monkeypatch):
    requests = mock_apify(monkeypatch)
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", ["Python"])
    assert result["status"] == "fresh" and result["count"] == 1
    assert len(requests) == 3
    assert "test-secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_apify_auth_failure_is_actionable_without_leaking_token(monkeypatch):
    mock_apify(monkeypatch, error=401)
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", [])
    assert result["status"] == "unavailable" and result["count"] is None
    assert "test-secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_old_apify_run_stays_stale_despite_recent_dataset_modification(monkeypatch):
    mock_apify(monkeypatch, age_hours=96)
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", [])
    assert result["status"] == "stale"


@pytest.mark.asyncio
async def test_dataset_update_is_not_assumed_to_be_collection_date(monkeypatch):
    mock_apify(monkeypatch, dataset_only=True)
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", [])
    assert result["status"] == "partial" and result["collectedAt"] is None


@pytest.mark.asyncio
async def test_empty_real_dataset_reports_zero(monkeypatch):
    mock_apify(monkeypatch, items=[])
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", [])
    assert result["count"] == 0 and result["status"] == "fresh"


@pytest.mark.asyncio
async def test_apify_paginates_and_discloses_cap(monkeypatch):
    requests = mock_apify(monkeypatch, items=[job(companyName=f"Company {i}") for i in range(520)])
    result = await provider.apify_jobs(["Mechatronics Engineer"], "QLD", [])
    assert result["scannedCount"] == 500 and result["truncated"] is True
    assert result["count"] == 500 and len(result["roles"]) == 20
    assert len([r for r in requests if r.url.path.endswith('/items')]) == 2
