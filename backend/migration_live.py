"""Live checks that sit beside the rulebook: published visa charges and state program notices.

Each check is independent, cached, time-limited and optional. A failure leaves the rulebook
value in place and is reported, never hidden.
"""
from __future__ import annotations

import asyncio
import re
import time

from bs4 import BeautifulSoup
from cachetools import TTLCache

import migration_rules as R
from intelligence import clean, expand_home_affairs, fetch, now_iso

_fee_cache: TTLCache = TTLCache(maxsize=32, ttl=60 * 60 * 12)
_state_cache: TTLCache = TTLCache(maxsize=16, ttl=60 * 60 * 6)
_failures: TTLCache = TTLCache(maxsize=64, ttl=60 * 10)


def parse_fee(html: str) -> int | None:
    """Return the primary 'From AUD' charge shown on a Home Affairs visa listing page."""
    text = clean(expand_home_affairs(html).get_text(" ", strip=True))
    patterns = [r"Cost\s*:?\s*From\s*AUD\s*\$?\s*([\d,]+(?:\.\d{2})?)", r"From\s*AUD\s*\$?\s*([\d,]+(?:\.\d{2})?)", r"Cost\s*:?\s*AUD\s*\$?\s*([\d,]+(?:\.\d{2})?)"]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match[1].replace(",", ""))
            if 100 <= value <= 30000:
                return int(round(value))
    return None


STATUS_PATTERN = re.compile(r"[^.]{0,220}\b(?:now open|now closed|are open|are closed|is open|is closed|currently open|currently closed|has opened|have opened|reopen(?:ed|s)?|will open|opening date|closed for|open for|registrations? of interest)[^.]{0,220}\.", re.I)


def parse_state_status(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = clean(soup.get_text(" ", strip=True))
    for match in STATUS_PATTERN.finditer(text):
        sentence = clean(match[0])
        if 25 <= len(sentence) <= 400 and re.search(r"20\d\d|program|nomination|ROI|registration", sentence, re.I):
            return sentence
    return None


async def _guard(key, coro, timeout):
    if key in _failures:
        return None
    try:
        return await asyncio.wait_for(coro, timeout)
    except Exception as exc:  # network, parse or timeout
        _failures[key] = type(exc).__name__
        return None


async def live_fee(code: str, timeout=8):
    if code in _fee_cache:
        return dict(_fee_cache[code], cached=True)
    url = R.VISA_URL.get(code)
    if not url:
        return None
    html = await _guard(f"fee:{code}", fetch(url), timeout)
    amount = parse_fee(html) if html else None
    if amount is None:
        return None
    result = {"amount": amount, "checkedAt": now_iso(), "sourceUrl": url, "ts": time.time()}
    _fee_cache[code] = result
    return result


async def live_state(code: str, timeout=8):
    if code in _state_cache:
        return dict(_state_cache[code], cached=True)
    info = R.STATES[code]
    html = await _guard(f"state:{code}", fetch(info["url"]), timeout)
    excerpt = parse_state_status(html) if html else None
    if not excerpt:
        return None
    result = {"excerpt": excerpt, "checkedAt": now_iso(), "sourceUrl": info["url"]}
    _state_cache[code] = result
    return result


async def gather_live(codes=("485", "482", "186", "494", "189", "190", "491", "191", "820", "858", "500"), states=tuple(R.STATES)):
    fee_tasks = {code: live_fee(code) for code in codes}
    state_tasks = {code: live_state(code) for code in states}
    fee_results = await asyncio.gather(*fee_tasks.values())
    state_results = await asyncio.gather(*state_tasks.values())
    fees = {code: value for code, value in zip(fee_tasks, fee_results) if value}
    state_status = {code: value for code, value in zip(state_tasks, state_results) if value}
    return {"fees": fees, "states": state_status,
            "report": {"feesLive": sorted(fees), "feesFallback": sorted(set(codes) - set(fees)), "statesLive": sorted(state_status), "statesFallback": sorted(set(states) - set(state_status)), "checkedAt": now_iso()}}
