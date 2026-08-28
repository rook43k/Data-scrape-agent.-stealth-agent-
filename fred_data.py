"""
FRED (Federal Reserve Economic Data) integration.

This is the single highest-signal free source for gold's #1 fundamental
driver: real yields. It requires a free API key (instant signup, no
approval wait) from https://fred.stlouisfed.org/docs/api/api_key.html

If FRED_API_KEY is not set, every function here returns None and the
report will note that real-yield data was skipped -- the rest of the
system still works without it.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from config import FRED_API_KEY, FRED_SERIES, REQUEST_TIMEOUT, USER_AGENT

log = logging.getLogger("xau_fundamentals.fred")

BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


@dataclass
class FredPoint:
    key: str
    label: str
    value: Optional[float] = None
    date: Optional[str] = None
    prev_value: Optional[float] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.value is not None


def _fetch_series(series_id: str, limit: int = 10) -> Optional[list[dict]]:
    if not FRED_API_KEY:
        return None
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        return data.get("observations", [])
    except Exception as exc:
        log.debug("FRED fetch failed for %s: %s", series_id, exc)
        return None


def fetch_point(key: str) -> FredPoint:
    cfg = FRED_SERIES[key]
    label = cfg["label"]

    if not FRED_API_KEY:
        return FredPoint(key=key, label=label, error="FRED_API_KEY not set -- skipped (optional).")

    obs = _fetch_series(cfg["id"], limit=10)
    if not obs:
        return FredPoint(key=key, label=label, error="No data returned from FRED.")

    # FRED uses "." for missing values on non-trading days -- skip those
    clean = [o for o in obs if o.get("value") not in (None, ".", "")]
    if not clean:
        return FredPoint(key=key, label=label, error="All recent FRED observations were missing.")

    latest = clean[0]
    value = float(latest["value"])
    date = latest["date"]
    prev_value = float(clean[1]["value"]) if len(clean) > 1 else None

    return FredPoint(key=key, label=label, value=value, date=date, prev_value=prev_value)


def fetch_all_points() -> dict[str, FredPoint]:
    return {key: fetch_point(key) for key in FRED_SERIES}


def compute_cpi_yoy(points: dict[str, FredPoint]) -> Optional[float]:
    """
    CPIAUCSL is a level index, not a YoY rate -- FRED's 'latest 10 obs' won't
    span a year for a monthly series, so this needs its own longer pull.
    """
    if not FRED_API_KEY:
        return None
    obs = _fetch_series("CPIAUCSL", limit=14)
    if not obs:
        return None
    clean = [o for o in obs if o.get("value") not in (None, ".", "")]
    if len(clean) < 13:
        return None
    latest = float(clean[0]["value"])
    year_ago = float(clean[12]["value"])
    return (latest - year_ago) / year_ago * 100.0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pts = fetch_all_points()
    for k, p in pts.items():
        if p.ok:
            print(f"{p.label:35s} {p.value:>8.3f}  (as of {p.date})")
        else:
            print(f"{p.label:35s} SKIPPED -- {p.error}")
    yoy = compute_cpi_yoy(pts)
    print(f"{'CPI YoY %':35s} {yoy if yoy is not None else 'N/A'}")
