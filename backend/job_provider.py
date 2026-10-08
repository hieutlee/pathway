"""Read completed Apify results without starting paid actor runs on dashboard loads."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import httpx
from bs4 import BeautifulSoup

from intelligence import STATES, clean, norm, now_iso, state_code

APIFY_API = "https://api.apify.com/v2"
FIELDS = {
    "title": ["title", "jobTitle", "positionName", "position"],
    "company": ["company.name", "company.display_name", "companyName", "company", "advertiser.description", "employer.name"],
    "location": ["location.display_name", "location.name", "location", "jobLocation", "locations.0.label", "locations.0.description"],
    "description": ["descriptionText", "description", "jobDescription", "descriptionHtml"],
    "url": ["jobUrl", "jobURL", "url", "link", "jobLink", "redirect_url"],
    "postedAt": ["postedAt", "datePosted", "listingDate", "publishedAt", "postedTime", "created"],
    "salary": ["salaryInfo", "salary", "salaryText", "salaryDescription"],
}


def field(item, path):
    for key in path.split("."):
        if isinstance(item, dict):
            item = item.get(key)
        elif isinstance(item, list) and key.isdigit() and int(key) < len(item):
            item = item[int(key)]
        else:
            return None
    return item


def as_text(value):
    if isinstance(value, (str, int, float)):
        return clean(value)
    if isinstance(value, dict):
        return ", ".join(str(value[k]) for k in ("city", "state", "country") if isinstance(value.get(k), str))
    if isinstance(value, list):
        return ", ".join(filter(None, (as_text(v) for v in value)))
    return ""


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result
    except ValueError:
        return None


def token_match(needle, haystack):
    return bool(needle and re.search(r"(?<![a-z0-9])" + re.escape(needle.lower()) + r"(?![a-z0-9])", haystack.lower()))


def normalize_job(item, mapping=None):
    if not isinstance(item, dict):
        return None
    values = {}
    for key, defaults in FIELDS.items():
        paths = [mapping[key]] if mapping and key in mapping else defaults
        values[key] = next((text for path in paths if (text := as_text(field(item, path)))), "")
    url = urlparse(values["url"])
    if not values["title"] or url.scheme not in {"http", "https"} or not url.hostname or url.username:
        return None
    if item.get("isExpired") is True or item.get("isClosed") is True or item.get("isActive") is False:
        return None
    expires = timestamp(item.get("validThrough") or item.get("expiresAt") or item.get("expireAt"))
    if expires and expires < datetime.now(timezone.utc):
        return None
    values["description"] = clean(BeautifulSoup(values["description"], "html.parser").get_text(" "))[:8000]
    return values


def rank_jobs(items, search_roles, state, skills, mapping=None, dataset_state=""):
    code = state_code(state)
    cities = {"QLD": ["brisbane", "gold coast", "sunshine coast", "townsville", "cairns"], "NSW": ["sydney", "newcastle", "wollongong"],
              "VIC": ["melbourne", "geelong"], "WA": ["perth"], "SA": ["adelaide"], "TAS": ["hobart", "launceston"], "NT": ["darwin"], "ACT": ["canberra"]}
    results, seen = [], set()
    for item in items:
        job = normalize_job(item, mapping)
        if job is None:
            continue
        location = norm(job["location"])
        location_matches = bool(code and any(token_match(place, location) for place in [code.lower(), STATES[code].lower(), *cities.get(code, [])]))
        if not location and code and state_code(dataset_state) == code:
            job["location"] = f"{code} (provider search scope)"
            location_matches = True
        if not location_matches:
            continue
        title = norm(job["title"])
        matching_titles = [role for role in search_roles if token_match(norm(role), title)]
        if not matching_titles:
            continue
        haystack = job["title"] + " " + job["description"]
        matched = [skill for skill in dict.fromkeys(skills) if token_match(skill, haystack)]
        # Preserve distinct jobs at different locations; remove tracking duplicate URLs.
        key = (norm(job["title"]), norm(job["company"]), norm(job["location"]))
        if key in seen:
            continue
        seen.add(key)
        job.update({"matchedSkills": matched, "matchedRole": matching_titles[0],
                    "reason": f"Title matches {matching_titles[0]}. " + (f"Skills mentioned: {', '.join(matched)}." if matched else "No supplied skills were found verbatim in the listing text.")})
        job.pop("description", None)
        results.append(job)
    return sorted(results, key=lambda job: (-len(job["matchedSkills"]), job["title"], job["company"]))


def configuration():
    return {"token": os.getenv("APIFY_TOKEN", ""), "task": os.getenv("APIFY_TASK_ID", ""), "dataset": os.getenv("APIFY_DATASET_ID", "")}


async def apify_jobs(search_roles, state, skills):
    config = configuration()
    base = {"source": "Apify job dataset", "sourceUrl": "https://console.apify.com/", "checkedAt": now_iso(),
            "searchRoles": search_roles, "roles": [], "count": None,
            "matchingMethod": "Matching role title and selected state, ordered by count of supplied skills mentioned in each listing."}
    if not config["token"] or not (config["task"] or config["dataset"]):
        return {**base, "status": "not_configured", "freshness": "Connection required", "provider": "Apify",
                "requiresConfiguration": ["APIFY_TOKEN", "APIFY_TASK_ID or APIFY_DATASET_ID"],
                "note": "Job listings will appear after the Apify connection is configured. No vacancy search has been completed."}
    if not state_code(state):
        return {**base, "status": "partial", "note": "Choose a recognised Australian state or territory before matching vacancies.", "freshness": "Location needed"}
    try:
        mapping = json.loads(os.getenv("APIFY_FIELD_MAP", "{}"))
        if not isinstance(mapping, dict) or any(k not in FIELDS or not isinstance(v, str) for k, v in mapping.items()):
            raise ValueError("invalid_field_map")
        max_items = max(1, min(5000, int(os.getenv("APIFY_MAX_ITEMS", "500"))))
        max_age = max(1, float(os.getenv("APIFY_MAX_AGE_HOURS", "48")))
        dataset_id = config["dataset"]
        collected_at = None
        async with httpx.AsyncClient(timeout=20, headers={"Authorization": f"Bearer {config['token']}"}) as client:
            if config["task"]:
                response = await client.get(f"{APIFY_API}/actor-tasks/{quote(config['task'], safe='~')}/runs/last", params={"status": "SUCCEEDED"})
                response.raise_for_status()
                run = response.json().get("data") or {}
                if run.get("status") != "SUCCEEDED" or not run.get("defaultDatasetId"):
                    raise ValueError("no_successful_run")
                dataset_id = run["defaultDatasetId"]
                collected_at = run.get("finishedAt")
            metadata = await client.get(f"{APIFY_API}/datasets/{quote(dataset_id, safe='~')}")
            metadata.raise_for_status()
            dataset = metadata.json().get("data") or {}
            # modifiedAt is a dataset update time, not proof of when any job was advertised.
            total = dataset.get("itemCount")
            items = []
            offset = 0
            while offset < max_items:
                limit = min(250, max_items - offset)
                response = await client.get(f"{APIFY_API}/datasets/{quote(dataset_id, safe='~')}/items",
                                            params={"format": "json", "clean": "true", "offset": offset, "limit": limit})
                response.raise_for_status()
                batch = response.json()
                if not isinstance(batch, list):
                    raise ValueError("unexpected_dataset_shape")
                items.extend(batch)
                offset += len(batch)
                if len(batch) < limit or (isinstance(total, int) and offset >= total):
                    break
        roles = rank_jobs(items, search_roles, state, skills, mapping, os.getenv("APIFY_JOBS_STATE", ""))
        readable = [normalize_job(item, mapping) for item in items]
        if items and not any(readable):
            return {**base, "status": "partial", "freshness": "Listing fields need attention", "note": "The dataset returned rows, but no active listing had both a recognised title and a valid listing URL. Check the actor output and field mapping."}
        date = timestamp(collected_at)
        age = (datetime.now(timezone.utc) - date).total_seconds() / 3600 if date else None
        status = "fresh" if age is not None and 0 <= age <= max_age else "stale" if age is not None else "partial"
        return {**base, "status": status, "freshness": "Collected results available" if status == "fresh" else "Older collection" if status == "stale" else "Collection time unknown",
                "roles": roles[:20], "count": len(roles), "returnedCount": min(20, len(roles)), "scannedCount": len(items),
                "datasetItemCount": total, "truncated": isinstance(total, int) and total > len(items),
                "collectedAt": collected_at, "datasetUpdatedAt": dataset.get("modifiedAt"), "provider": "Apify",
                "note": f"{len(roles)} matching listings among {len(items)} retrieved dataset rows. This is not the total Australian vacancy count. Check each advert for current availability."}
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        note = "Apify could not return a usable dataset. Check the task or dataset configuration and retry."
        if status_code in {401, 403}:
            note = "Apify rejected the connection credentials or dataset access."
        elif status_code == 404:
            note = "The configured Apify task or dataset was not found, or the task has no successful run yet."
        return {**base, "status": "unavailable", "freshness": "Provider request failed", "note": note, "error": type(exc).__name__}


async def adzuna_jobs(search_roles, state, skills):
    """Retain the original optional provider, using evidence instead of fit percentages."""
    base = {"source": "Adzuna Australia", "sourceUrl": "https://www.adzuna.com.au/", "checkedAt": now_iso(),
            "searchRoles": search_roles, "roles": [], "count": None, "provider": "Adzuna"}
    try:
        items = []
        async with httpx.AsyncClient(timeout=15) as client:
            for role in search_roles[:3]:
                response = await client.get("https://api.adzuna.com/v1/api/jobs/au/search/1", params={
                    "app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"],
                    "what": role, "where": state, "results_per_page": 20, "content-type": "application/json"})
                response.raise_for_status()
                items.extend(response.json().get("results", []))
        roles = rank_jobs(items, search_roles, state, skills)
        return {**base, "status": "fresh", "freshness": "Provider search completed", "collectedAt": base["checkedAt"],
                "roles": roles[:20], "count": len(roles), "scannedCount": len(items), "returnedCount": min(len(roles), 20),
                "note": f"{len(roles)} matching listings among {len(items)} retrieved Adzuna results. Check each advert for current availability."}
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        return {**base, "status": "unavailable", "freshness": "Provider request failed", "note": "Adzuna could not return current listings. Check the provider credentials and retry.", "error": type(exc).__name__}
