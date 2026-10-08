"""Persistent, shared advert cache. A request creates at most one Apify run.

Polling reads the persisted run; it never starts a replacement. Profiles are only
used in memory to analyse the shared adverts and are never sent to Apify.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import httpx

from intelligence import STATES, clean, norm, now_iso
from job_analysis import analyse
from job_provider import APIFY_API, timestamp

ACTOR_ID = "hKByXkMQaC5Qt9UMN"
CITIES = {"brisbane": "QLD", "gold coast": "QLD", "sunshine coast": "QLD", "townsville": "QLD", "cairns": "QLD", "sydney": "NSW", "newcastle": "NSW", "wollongong": "NSW", "melbourne": "VIC", "geelong": "VIC", "perth": "WA", "adelaide": "SA", "hobart": "TAS", "launceston": "TAS", "darwin": "NT", "canberra": "ACT"}


def location_name(value):
    value = norm(value).replace(",", " ")
    value = re.sub(r"\baustralia\b", "", value).strip()
    if not value:
        return "Australia"
    for code, full in STATES.items():
        value = re.sub(r"\b"+re.escape(full.lower())+r"\b", code.lower(), value)
    value = clean(value)
    for city, code in CITIES.items():
        if value in {city, city+" "+code.lower()}:
            return f"{city.title()}, {code}, Australia"
    if value.upper() in STATES:
        return f"{STATES[value.upper()]}, Australia"
    return value.title()+", Australia"


@dataclass
class Settings:
    token: str = ""
    task: str = ""
    seed_run: str = ""
    enable_runs: bool = False
    limit: int = 10
    ttl_hours: float = 48
    max_charge: float = 0.50
    daily_runs: int = 5
    timeout: int = 180
    db_path: str = str(Path(__file__).with_name("data") / "jobs.sqlite3")

    @classmethod
    def from_env(cls):
        return cls(token=os.getenv("APIFY_TOKEN", ""), task=os.getenv("APIFY_TASK_ID", ""), seed_run=os.getenv("APIFY_SEED_RUN_ID", ""),
                   enable_runs=os.getenv("APIFY_ENABLE_RUNS", "false").lower()=="true",
                   limit=max(1, min(200, int(os.getenv("APIFY_SEARCH_LIMIT", "10")))),
                   ttl_hours=max(1, min(168, float(os.getenv("APIFY_MAX_AGE_HOURS", "48")))),
                   max_charge=max(0.01, min(10, float(os.getenv("APIFY_MAX_CHARGE_USD", "0.50")))),
                   daily_runs=max(1, min(100, int(os.getenv("APIFY_DAILY_RUN_LIMIT", "5")))),
                   timeout=max(30, min(600, int(os.getenv("APIFY_RUN_TIMEOUT_SECONDS", "180")))),
                   db_path=os.getenv("JOBS_CACHE_PATH", cls.db_path))


def query_spec(role, location, window, settings):
    return {"role": clean(role), "location": location_name(location), "dateWindow": window,
            "limit": settings.limit, "distanceMiles": 25, "provider": ACTOR_ID, "version": 1}


def query_key(spec):
    canonical = {**spec, "role": norm(spec["role"]), "location": location_name(spec["location"])}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS searches (
                  key TEXT PRIMARY KEY, query TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'idle',
                  run_id TEXT, updated REAL NOT NULL, note TEXT NOT NULL DEFAULT '', snapshot TEXT);
                CREATE TABLE IF NOT EXISTS snapshots (
                  id INTEGER PRIMARY KEY, key TEXT NOT NULL, run_id TEXT UNIQUE, collected_at TEXT, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reservations (
                  id INTEGER PRIMARY KEY, key TEXT NOT NULL, at REAL NOT NULL, charge REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM searches WHERE key=?", (key,)).fetchone()
        return dict(row) if row else None

    def meta(self, key, value=None):
        with self.connect() as db:
            if value is not None:
                db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key,value))
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def claim_seed(self, key):
        with self.connect() as db:
            marker = "Checking saved collection:"+str(time.time())
            result = db.execute("INSERT OR IGNORE INTO meta VALUES (?,?)", (key, marker))
            if result.rowcount == 1:
                return True
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            # A crashed import is safe to retry: this operation is strictly read only.
            if row and row[0].startswith("Checking saved collection:") and time.time()-float(row[0].split(":",1)[1])>120:
                return db.execute("UPDATE meta SET value=? WHERE key=? AND value=?", (marker,key,row[0])).rowcount==1
            return False

    def save(self, spec, snapshot):
        key = query_key(spec)
        encoded = json.dumps(snapshot)
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO snapshots(key,run_id,collected_at,data) VALUES (?,?,?,?)", (key, snapshot["runId"], snapshot["collectedAt"], encoded))
            existing = db.execute("SELECT snapshot FROM searches WHERE key=?", (key,)).fetchone()
            old = json.loads(existing[0]) if existing and existing[0] else None
            if old and (timestamp(old["collectedAt"]) or datetime.min.replace(tzinfo=timezone.utc)) > (timestamp(snapshot["collectedAt"]) or datetime.min.replace(tzinfo=timezone.utc)):
                return
            db.execute("INSERT INTO searches(key,query,state,updated,snapshot) VALUES (?,?,'ready',?,?) ON CONFLICT(key) DO UPDATE SET state='ready',updated=excluded.updated,note='',snapshot=excluded.snapshot,run_id=NULL", (key,json.dumps(spec),time.time(),encoded))

    def state(self, key, state, note="", run_id=None):
        with self.connect() as db:
            db.execute("UPDATE searches SET state=?,note=?,run_id=?,updated=? WHERE key=?", (state,note,run_id,time.time(),key))

    def reserve(self, spec, settings):
        key, now = query_key(spec), time.time()
        midnight = datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM searches WHERE key=?", (key,)).fetchone()
            if row:
                if row["state"] in {"starting", "running", "unknown"}:
                    return False
                if row["snapshot"]:
                    collected = timestamp(json.loads(row["snapshot"])["collectedAt"])
                    if collected and 0 <= now-collected.timestamp() < settings.ttl_hours*3600:
                        return False
                if row["state"]=="failed" and now-row["updated"] < 3600:
                    return False
            used = db.execute("SELECT COUNT(*) FROM reservations WHERE at>=?", (midnight,)).fetchone()[0]
            state = "blocked" if used >= settings.daily_runs else "starting"
            note = "The daily collection limit has been reached. Cached adverts remain available. Try again tomorrow." if state=="blocked" else "Starting a bounded collection."
            db.execute("INSERT INTO searches(key,query,state,updated,note) VALUES (?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET state=excluded.state,updated=excluded.updated,note=excluded.note,run_id=NULL", (key,json.dumps(spec),state,now,note))
            if state=="blocked":
                return False
            db.execute("INSERT INTO reservations(key,at,charge) VALUES (?,?,?)", (key,now,settings.max_charge))
            return True


class Apify:
    def __init__(self, settings):
        self.settings = settings

    async def request(self, method, path, **kwargs):
        async with httpx.AsyncClient(timeout=20, headers={"Authorization": "Bearer "+self.settings.token}) as client:
            response = await client.request(method, APIFY_API+path, **kwargs)
            response.raise_for_status()
            return response.json()

    async def run(self, run_id):
        return (await self.request("GET", "/actor-runs/"+quote(run_id,safe="")))["data"]

    async def input(self, run):
        return await self.request("GET", "/key-value-stores/"+quote(run["defaultKeyValueStoreId"],safe="")+"/records/INPUT")

    async def task(self):
        return (await self.request("GET", "/actor-tasks/"+quote(self.settings.task,safe="~")))["data"]

    async def start(self, spec):
        body = {"keywords": spec["role"], "location": spec["location"], "datePosted": spec["dateWindow"],
                "urls": [], "geoId": "", "companyIds": [], "under10Applicants": False,
                "splitByLocation": False, "splitCountry": "AU", "scrapeCompany": False,
                "autoConvertToAiSearch": True, "distance": spec["distanceMiles"], "limitPerSource": spec["limit"]}
        return (await self.request("POST", "/actor-tasks/"+quote(self.settings.task,safe="~")+"/runs", json=body,
                                   params={"timeout": self.settings.timeout, "maxTotalChargeUsd": self.settings.max_charge,
                                           "maxItems": spec["limit"], "restartOnError": "false", "waitForFinish": 0}))["data"]

    async def snapshot(self, run, spec, provenance):
        if run.get("status")!="SUCCEEDED" or run.get("actId")!=ACTOR_ID or not timestamp(run.get("finishedAt")):
            raise ValueError("Collection has no verified completion time or actor.")
        dataset = quote(run["defaultDatasetId"],safe="")
        meta = (await self.request("GET", "/datasets/"+dataset))["data"]
        items = []
        while len(items) < spec["limit"]:
            limit = min(100, spec["limit"]-len(items))
            batch = await self.request("GET", "/datasets/"+dataset+"/items", params={"format":"json", "clean":"true", "offset":len(items), "limit":limit})
            if not isinstance(batch, list):
                raise ValueError("Collection did not contain a list of adverts.")
            items.extend(batch[:limit])
            if len(batch)<limit:
                break
        return {"items":items, "runId":run["id"], "collectedAt":run["finishedAt"], "datasetItemCount":meta.get("itemCount"),
                "capped": len(items)>=spec["limit"], "provenance":provenance, "query":spec}


def seed_spec(input_data, settings):
    """Recover the original query. Never relabel a seed as the client's search."""
    role, location = input_data.get("keywords"), input_data.get("location")
    window = input_data.get("datePosted") or "anyTime"
    if input_data.get("splitByLocation") or input_data.get("companyIds") or input_data.get("under10Applicants"):
        return None
    urls = input_data.get("urls") or []
    if urls:
        if len(urls)!=1:
            return None
        raw = urls[0] if isinstance(urls[0],str) else urls[0].get("url", "")
        parsed = urlparse(raw)
        if not parsed.hostname or not (parsed.hostname=="linkedin.com" or parsed.hostname.endswith(".linkedin.com")):
            return None
        params = parse_qs(parsed.query)
        # Unknown or restrictive filters make this a different sample.
        if any(k.startswith("f_") and k!="f_TPR" for k in params) or params.get("geoId"):
            return None
        role = (params.get("keywords") or [None])[0]
        location = (params.get("location") or [None])[0]
        window = {"": "anyTime", "r86400": "past24Hours", "r604800": "pastWeek", "r2592000": "pastMonth"}.get((params.get("f_TPR") or [""])[0])
        distance = (params.get("distance") or [25])[0]
    else:
        if input_data.get("geoId"):
            return None
        distance = input_data.get("distance",25)
    if not role or not location or window not in {"anyTime", "past24Hours", "pastWeek", "pastMonth"}:
        return None
    try:
        if float(distance or 25)!=25:
            return None
        original_limit = input_data.get("limitPerSource")
        if original_limit and int(original_limit)<settings.limit:
            return None
    except (ValueError,TypeError):
        return None
    return query_spec(role, location, window, settings)


async def import_seed(store, provider, settings):
    if not settings.seed_run:
        return ""
    key = "seed:"+settings.seed_run+":"+str(settings.limit)
    if not store.claim_seed(key):
        return store.meta(key) or "Checking saved collection:"+str(time.time())
    note = ""
    try:
        run = await provider.run(settings.seed_run)
        spec = seed_spec(await provider.input(run), settings)
        if spec is None:
            note = "The existing run's precise role, location or filters could not be verified. It has not been assigned to this search."
        else:
            snapshot = await provider.snapshot(run, spec, "Imported completed run; scope verified from saved INPUT")
            store.save(spec,snapshot)
            note = f"Existing run cached for {spec['role']} in {spec['location']} ({spec['dateWindow']})."
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        # Retry read-only import later, e.g. after token permissions are corrected.
        note = "The existing run could not be read. Check permission to read the run, its INPUT record and dataset."
        with store.connect() as db:
            db.execute("DELETE FROM meta WHERE key=?", (key,))
        return note
    store.meta(key,note)
    return note


def response_payload(spec, row, profile, settings, note="", seed_note="", cached=True):
    snapshot = json.loads(row["snapshot"]) if row and row["snapshot"] else None
    state = row["state"] if row else "idle"
    base = {"queryId":query_key(spec), "query":spec, "status":"not_configured", "count":None, "roles":[],
            "source":"LinkedIn adverts via Apify", "provider":"Apify", "sourceUrl":"https://console.apify.com/actors/tasks/"+quote(settings.task,safe="~")+"/runs",
            "checkedAt":now_iso(), "collectionState":state, "seedNote":seed_note, "pollAfterSeconds":4 if state in {"starting","running"} else None,
            "note":note or (row["note"] if row else ""), "searchRoles":[spec["role"]]}
    if not snapshot:
        base["status"] = "loading" if state in {"starting","running"} else "unavailable" if row else "not_configured"
        base["freshness"] = "Collecting adverts" if base["status"]=="loading" else "Collection unavailable"
        return base
    collected = timestamp(snapshot["collectedAt"])
    age = time.time()-collected.timestamp() if collected else None
    fresh = age is not None and 0<=age<settings.ttl_hours*3600
    intelligence = analyse(snapshot["items"],profile,spec["role"])
    malformed = bool(snapshot["items"]) and not intelligence["roles"]
    status = "partial" if malformed else "fresh" if fresh else "stale"
    count = intelligence["count"]
    note = f"{count} distinct active adverts from {len(snapshot['items'])} retrieved rows for this provider search. "
    note += "Collection limit reached. " if snapshot["capped"] else ""
    note += "This is a sample, not the total number of vacancies. The provider may return nearby places and related titles."
    if malformed:
        note = "Rows were returned, but no active advert had a recognised title and link. A vacancy count cannot be established."
    if not fresh:
        note += " These are older results."
    return {**base, **intelligence, "count":None if malformed else count, "status":status, "cached":cached,
            "scannedCount":len(snapshot["items"]), "returnedCount":count, "datasetItemCount":snapshot["datasetItemCount"],
            "truncated":snapshot["capped"], "collectedAt":snapshot["collectedAt"], "runId":snapshot["runId"],
            "provenance":snapshot["provenance"], "sourceUrl":f"https://console.apify.com/actors/{ACTOR_ID}/runs/{snapshot['runId']}",
            "note":note, "collectionNote":base["note"], "freshness":"Recent cached collection" if fresh else "Older collection"}


async def search_jobs(role, location, profile, window="anyTime", start_if_missing=True, settings=None, provider=None):
    settings = settings or Settings.from_env()
    spec = query_spec(role,location,window,settings)
    store, key = Store(settings.db_path), query_key(spec)
    provider = provider or Apify(settings)
    row = store.get(key)
    if not settings.token:
        payload = response_payload(spec,row,profile,settings,"Connect Apify to collect adverts. Existing cached results remain available.")
        payload["pollAfterSeconds"] = None
        if not row or not row["snapshot"]:
            payload.update(status="not_configured", collectionState="idle")
        return payload
    seed_note = await import_seed(store,provider,settings)
    if seed_note.startswith("The existing run could not be read"):
        # Do not pay for a possible duplicate just because an existing run is unreadable.
        payload = response_payload(spec,row,profile,settings,seed_note,seed_note)
        if not row or not row["snapshot"]:
            payload["status"] = "unavailable"
        return payload
    if seed_note.startswith("Checking saved collection:"):
        payload = response_payload(spec,row,profile,settings,"Checking the existing collection before starting a new one.")
        payload.update(status="loading" if not row or not row["snapshot"] else payload["status"],
                       collectionState="checking_cache", pollAfterSeconds=4, pollStartIfMissing=start_if_missing)
        return payload
    row = store.get(key)
    if row and row["state"]=="starting" and time.time()-row["updated"]>60:
        store.state(key,"unknown","The run start was interrupted. Check Apify before restarting this search; an accepted run may already have charged. See recovery steps in README.")
        row = store.get(key)
    if row and row["state"]=="running":
        try:
            run = await provider.run(row["run_id"])
            if run["status"]=="SUCCEEDED":
                store.save(spec,await provider.snapshot(run,spec,"Collected with explicit search input"))
            elif run["status"] in {"FAILED","TIMED-OUT","ABORTED"}:
                store.state(key,"failed",f"Collection ended with {run['status']}. Partial results were not counted. Retry after one hour.",row["run_id"])
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            return response_payload(spec,row,profile,settings,"The collection is still being checked. No replacement run has been started.",seed_note)
        return response_payload(spec,store.get(key),profile,settings,seed_note=seed_note,cached=False)
    if row and row["snapshot"]:
        stamp = timestamp(json.loads(row["snapshot"])["collectedAt"])
        if stamp and 0<=time.time()-stamp.timestamp()<settings.ttl_hours*3600:
            return response_payload(spec,row,profile,settings,seed_note=seed_note)
    if row and row["state"] in {"starting","unknown"}:
        return response_payload(spec,row,profile,settings,seed_note=seed_note)
    if not start_if_missing or not settings.enable_runs or not settings.task:
        note = "No recent collection for this exact search. New collections are disabled in backend settings." if not settings.enable_runs else "No recent collection. Use Search to request one."
        return response_payload(spec,row,profile,settings,note,seed_note)
    try:
        task = await provider.task()
        if task.get("actId")!=ACTOR_ID:
            return response_payload(spec,row,profile,settings,"The saved task does not use the configured LinkedIn jobs actor.",seed_note)
    except (httpx.HTTPError,KeyError,ValueError,TypeError):
        return response_payload(spec,row,profile,settings,"The saved task could not be read. Check token permissions and the task ID.",seed_note)
    if not store.reserve(spec,settings):
        return response_payload(spec,store.get(key),profile,settings,seed_note=seed_note)
    try:
        run = await provider.start(spec)
        if not run.get("id"):
            raise ValueError("Missing run ID")
        store.state(key,"running","Collecting this role and location. Other clients reuse this same collection.",run["id"])
    except httpx.HTTPStatusError as exc:
        # A server error can follow an accepted POST. Never blindly retry it.
        definitive = 400<=exc.response.status_code<500
        store.state(key,"failed" if definitive else "unknown", "Apify rejected the run request. Check settings or permissions; retry after one hour." if definitive else "The run start could not be confirmed. Check Apify before retrying. See recovery steps in README.")
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        store.state(key,"unknown","The run start could not be confirmed. Check Apify before retrying. See recovery steps in README.")
    return response_payload(spec,store.get(key),profile,settings,seed_note=seed_note,cached=False)
