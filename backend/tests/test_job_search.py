import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from job_analysis import analyse, corpus_jobs, experience_requirement, salary_evidence, seniority
from job_search import ACTOR_ID, Apify, Settings, Store, query_key, query_spec, search_jobs, seed_spec


def advert(i=1, **overrides):
    return {"title":"Mechatronics Engineer", "link":f"https://www.linkedin.com/jobs/view/{1000000+i}/?trk=test", "companyName":"Test Engineering", "location":"Brisbane, Queensland, Australia", "descriptionText":"We require a minimum of 3 years of experience in automation. Python and PLC skills are required.", "salaryInfo":["AUD 90,000 to 120,000 per annum plus super"], **overrides}


class FakeApify:
    def __init__(self, items=None, inputs=None):
        self.starts = 0
        self.items = items if items is not None else [advert()]
        self.inputs = inputs or {"keywords":"Mechatronics Engineer", "location":"Brisbane, QLD", "limitPerSource":10}
        self.fail_start = False
        self.run_status = "SUCCEEDED"
        self.date = datetime.now(timezone.utc).isoformat()

    async def task(self):
        await asyncio.sleep(0)
        return {"actId":ACTOR_ID}

    async def start(self, spec):
        self.starts += 1
        await asyncio.sleep(0)
        if self.fail_start:
            raise httpx.ReadTimeout("Ambiguous POST result")
        return {"id":f"new{self.starts}", "status":"RUNNING"}

    async def run(self, run_id):
        return {"id":run_id, "status":self.run_status, "actId":ACTOR_ID, "finishedAt":self.date}

    async def input(self, run):
        return self.inputs

    async def snapshot(self, run, spec, provenance):
        return {"items":self.items, "runId":run["id"], "collectedAt":self.date, "datasetItemCount":len(self.items), "capped":len(self.items)>=spec["limit"], "provenance":provenance, "query":spec}


@pytest.fixture
def settings(tmp_path):
    return Settings(token="test-secret",task="FcJaZmFO4ABzrGRZ1",enable_runs=True,db_path=str(tmp_path / "cache.sqlite3"))


async def search(settings, provider, **kwargs):
    return await search_jobs(kwargs.pop("role","Mechatronics Engineer"),kwargs.pop("location","Brisbane, QLD"),kwargs.pop("profile",{"skills":["Python"],"experienceYears":1}),settings=settings,provider=provider,**kwargs)


def test_query_isolation_and_normalization(settings):
    a=query_spec("Mechatronics Engineer","Brisbane, QLD","anyTime",settings)
    assert query_key(a)==query_key(query_spec("mechatronics engineer","Brisbane, Queensland, Australia","anyTime",settings))
    assert query_key(a)!=query_key(query_spec("Mechatronics Engineer","Queensland","anyTime",settings))
    assert query_key(a)!=query_key(query_spec("Mechatronics Engineer","Sydney, NSW","anyTime",settings))
    assert query_key(a)!=query_key(query_spec("Mechatronics Engineer","Brisbane","pastWeek",settings))
    settings.limit=20
    assert query_key(a)!=query_key(query_spec("Mechatronics Engineer","Brisbane","anyTime",settings))
    assert "profile" not in a


@pytest.mark.asyncio
async def test_concurrent_clients_start_one_run_and_persist(settings):
    provider=FakeApify()
    results=await asyncio.gather(*(search(settings,provider) for _ in range(10)))
    assert provider.starts==1
    assert all(r["collectionState"] in {"starting","running"} for r in results)
    done=await search(settings,provider,start_if_missing=False)
    assert done["count"]==1 and done["status"]=="fresh"
    again=await search(settings,provider)
    assert again["cached"] and provider.starts==1
    assert Store(settings.db_path).get(again["queryId"])["state"]=="ready"


@pytest.mark.asyncio
async def test_shared_market_personal_fit_and_no_profile_storage(settings):
    provider=FakeApify()
    await search(settings,provider)
    junior=await search(settings,provider,profile={"skills":["Python"],"experienceYears":1})
    experienced=await search(settings,provider,profile={"skills":["Python","PLC","PRIVATE_UNIQUE_SKILL"],"experienceYears":5})
    assert junior["market"]==experienced["market"]
    assert junior["roles"][0]["fit"]["label"]=="Stretch"
    assert experienced["roles"][0]["fit"]["label"]=="Strong evidence alignment"
    assert provider.starts==1
    assert b"PRIVATE_UNIQUE_SKILL" not in open(settings.db_path,"rb").read()


@pytest.mark.asyncio
async def test_seed_is_cached_for_its_actual_scope(settings):
    settings.seed_run="aScBU8lDVTdbXEDWQ"
    provider=FakeApify()
    result=await search(settings,provider)
    assert result["runId"]==settings.seed_run and provider.starts==0
    another=await search(settings,provider,location="Sydney, NSW")
    assert provider.starts==1 and another["count"] is None
    assert result["queryId"]!=another["queryId"]


@pytest.mark.asyncio
async def test_concurrent_seed_import_does_not_start_duplicate_paid_run(settings):
    settings.seed_run="seed"
    provider=FakeApify()
    original_run=provider.run
    async def slow_run(run_id):
        await asyncio.sleep(.02)
        return await original_run(run_id)
    provider.run=slow_run
    results=await asyncio.gather(*(search(settings,provider) for _ in range(10)))
    assert provider.starts==0
    assert all(r["count"]==1 or r["collectionState"]=="checking_cache" for r in results)
    ready=await search(settings,provider,start_if_missing=True)
    assert ready["count"]==1 and provider.starts==0


@pytest.mark.asyncio
async def test_unreadable_existing_run_does_not_trigger_paid_replacement(settings):
    settings.seed_run="seed"
    provider=FakeApify()
    async def unreadable(run_id):
        raise httpx.ReadTimeout("read failed")
    provider.run=unreadable
    result=await search(settings,provider)
    assert result["status"]=="unavailable" and provider.starts==0


@pytest.mark.asyncio
async def test_old_seed_remains_visible_when_new_runs_disabled(settings):
    settings.enable_runs=False
    settings.seed_run="seed"
    provider=FakeApify()
    provider.date=(datetime.now(timezone.utc)-timedelta(days=4)).isoformat()
    result=await search(settings,provider)
    assert result["status"]=="stale" and result["count"]==1 and provider.starts==0


def test_restricted_seed_not_relabelled(settings):
    assert seed_spec({"keywords":"Mechatronics Engineer", "location":"Australia", "geoId":"unknown"},settings) is None
    assert seed_spec({"urls":["https://www.linkedin.com/jobs/search/?keywords=Engineer&location=Brisbane&f_E=1"]},settings) is None
    spec=seed_spec({"urls":["https://www.linkedin.com/jobs/search/?keywords=Mechatronics%20Engineer&location=Brisbane%2C%20QLD&f_TPR=r604800"]},settings)
    assert spec["dateWindow"]=="pastWeek" and spec["location"]=="Brisbane, QLD, Australia"


@pytest.mark.asyncio
async def test_empty_success_is_cached_and_missing_configuration_not_zero(settings):
    provider=FakeApify(items=[])
    await search(settings,provider)
    done=await search(settings,provider,start_if_missing=False)
    assert done["count"]==0 and done["status"]=="fresh"
    await search(settings,provider)
    assert provider.starts==1
    settings.token=""
    missing=await search(settings,provider,location="Perth, WA")
    assert missing["count"] is None and missing["status"]=="not_configured"


@pytest.mark.asyncio
async def test_ambiguous_post_never_retried_automatically(settings):
    provider=FakeApify()
    provider.fail_start=True
    failed=await search(settings,provider)
    assert failed["collectionState"]=="unknown" and failed["pollAfterSeconds"] is None
    await search(settings,provider)
    assert provider.starts==1


@pytest.mark.asyncio
async def test_daily_budget_and_read_only_poll(settings):
    settings.daily_runs=1
    provider=FakeApify()
    await search(settings,provider,start_if_missing=False)
    assert provider.starts==0
    await search(settings,provider)
    result=await search(settings,provider,location="Sydney")
    assert result["collectionState"]=="blocked" and provider.starts==1
    assert "daily collection limit" in result["note"]


@pytest.mark.asyncio
async def test_stale_cache_survives_refresh_failure(settings):
    provider=FakeApify()
    spec=query_spec("Mechatronics Engineer","Brisbane","anyTime",settings)
    provider.date=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
    Store(settings.db_path).save(spec,await provider.snapshot({"id":"old"},spec,"test"))
    result=await search(settings,provider)
    assert result["status"]=="stale" and result["collectionState"]=="running"
    provider.run_status="FAILED"
    failed=await search(settings,provider,start_if_missing=False)
    assert failed["status"]=="stale" and failed["count"]==1
    await search(settings,provider)
    assert provider.starts==1


@pytest.mark.asyncio
async def test_provider_overrides_saved_search_and_caps_spend(settings):
    provider=Apify(settings)
    captured={}
    async def request(method,path,**kwargs):
        captured.update(method=method,path=path,**kwargs)
        return {"data":{"id":"new"}}
    provider.request=request
    await provider.start(query_spec("Nurse","Perth","pastWeek",settings))
    assert captured["json"]["urls"]==[] and captured["json"]["geoId"]==""
    assert captured["json"]["keywords"]=="Nurse"
    assert captured["json"]["limitPerSource"]==10
    assert captured["json"]["splitByLocation"] is False
    assert captured["params"]["maxTotalChargeUsd"]==0.5
    assert captured["params"]["restartOnError"]=="false"
    assert "profile" not in captured["json"] and "token" not in captured["params"]


def test_ambiguous_seniority_and_conflicting_junior_requirements():
    assert seniority("Engineer","Mid-Senior level",None)["level"]=="Unspecified"
    assert seniority("Engineer","Associate",None)["level"]=="Unspecified"
    requirement=experience_requirement("Applicants must have 3+ years of experience in PLC. We use AI tools.")
    assert requirement["minimum"]==3
    assert seniority("Junior Engineer","Mid-Senior level",requirement)["level"]=="Junior"
    assert experience_requirement("We have 25 years of experience. Ideally 5 years of experience in sales.") is None
    assert experience_requirement("3 years of experience preferred.") is None


def test_salary_period_currency_super_and_missing_data():
    annual=salary_evidence("AUD 90k to 120k per annum plus super")
    assert annual["min"]==90000 and annual["max"]==120000 and annual["basis"]=="Excludes super"
    assert salary_evidence("A$60 to A$75 per hour including super")["period"]=="hour"
    assert salary_evidence("$120,000 per year")["currency"]=="$ (currency unstated)"
    assert salary_evidence("USD 100k per year")["currency"]=="USD"
    assert salary_evidence("Competitive salary") is None
    assert salary_evidence("AUD 100,000") is None
    analysis=analyse([advert(1),advert(2,salaryInfo=["A$60 per hour including super"]),advert(3,salaryInfo=[])],{},"Engineer")
    assert len(analysis["market"]["all"]["salaries"])==2
    assert analysis["market"]["all"]["salaryDisclosedCount"]==2


def test_distinct_ids_reposts_and_evidence_based_counts():
    jobs=[advert(1,title="Junior Engineer",descriptionText="You must have 3 years of experience with Python and AI tools."),advert(2,title="Senior Engineer"),advert(1,link="https://www.linkedin.com/jobs/view/1000001/?trk=other",title="Junior Engineer"),advert(3,title="Engineer",descriptionText="We use PLC",seniorityLevel="Mid-Senior level")]
    result=analyse(jobs,{"skills":["Python"],"experienceYears":1},"Engineer")
    assert result["count"]==3
    market=result["market"]["all"]
    assert market["juniorDemand"]["count"]==1 and market["aiMentions"]["count"]==1
    assert sum(l["count"] for l in market["levels"])==3
    assert market["companies"]==[{"name":"Test Engineering","count":3}]
    assert market["juniorDemand"]["examples"][0]["url"]
    assert all("description" not in job for job in result["roles"])


@pytest.mark.asyncio
async def test_http_endpoint_rejects_invalid_inputs_and_ignores_private_profile_fields(monkeypatch):
    import main
    captured={}
    async def fake_search(role,location,profile,window,start):
        captured.update(profile=profile,role=role)
        return {"count":None,"status":"not_configured"}
    monkeypatch.setattr(main,"search_jobs",fake_search)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app),base_url="http://test") as client:
        bad=await client.post("/api/jobs/search",json={"role":"A","location":"Brisbane"})
        assert bad.status_code==422
        ok=await client.post("/api/jobs/search",json={"role":"Engineer","location":"Brisbane","profile":{"name":"PRIVATE NAME","resume":"PRIVATE RESUME","skills":["Python"],"experienceYears":0}})
        assert ok.status_code==200
        assert captured["profile"]=={"occupation":"","skills":["Python"],"experienceYears":0.0}
