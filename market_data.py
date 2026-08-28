"""
Market data fetching: prices and short-term changes for the instruments that
matter for XAUUSD fundamentals (gold itself, DXY, yields, oil, VIX, equities).

Strategy: try yfinance first (no key needed). If that fails -- Yahoo
sometimes rate-limits or changes its undocumented endpoints -- fall back to
Stooq's keyless CSV endpoint. Both are best-effort free sources, so every
function returns None on total failure rather than raising, and the caller
is expected to handle missing data gracefully (this is real-world market
data plumbing: sources go down, and the report should say so, not crash).
"""

from __future__ import annotations
import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from config import TICKERS, BREAKOUT_LOOKBACK_DAYS, REQUEST_TIMEOUT, USER_AGENT

log = logging.getLogger("xau_fundamentals.market_data")


@dataclass
class Quote:
    key: str
    label: str
    last: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    as_of: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.last is not None


def _try_yfinance(yf_symbol: str) -> Optional[tuple[float, float, str]]:
    """Returns (last, prev_close, as_of_iso) or None."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d", interval="1d")
        if hist is None or hist.empty or len(hist) < 1:
            return None
        last_row = hist.iloc[-1]
        last = float(last_row["Close"])
        if len(hist) >= 2:
            prev_close = float(hist.iloc[-2]["Close"])
        else:
            prev_close = float(last_row.get("Open", last))
        as_of = hist.index[-1].to_pydatetime().astimezone(timezone.utc).isoformat()
        return last, prev_close, as_of
    except Exception as exc:
        log.debug("yfinance failed for %s: %s", yf_symbol, exc)
        return None


def _try_stooq(stooq_symbol: str) -> Optional[tuple[float, float, str]]:
    """
    Stooq's keyless CSV quote endpoint. Undocumented but widely used and
    free with no signup. Returns (last, prev_close_approx, as_of) or None.
    Note: Stooq's free quote endpoint gives last price + date but not always
    a clean previous close, so prev_close is approximated from the daily
    history endpoint when available.
    """
    try:
        url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        row = next(reader, None)
        if not row or row.get("Close") in (None, "N/D", ""):
            return None
        last = float(row["Close"])
        date_str = row.get("Date", "")
        as_of = date_str or datetime.now(timezone.utc).date().isoformat()

        # try to get a real previous close from the daily history csv
        prev_close = last
        try:
            hist_url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
            hist_resp = requests.get(hist_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
            hist_resp.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(hist_resp.text)))
            if len(rows) >= 2:
                prev_close = float(rows[-2]["Close"])
        except Exception:
            pass

        return last, prev_close, as_of
    except Exception as exc:
        log.debug("stooq failed for %s: %s", stooq_symbol, exc)
        return None


def fetch_quote(key: str) -> Quote:
    """Fetch a single instrument by its TICKERS config key."""
    cfg = TICKERS[key]
    label = cfg["label"]

    result = _try_yfinance(cfg["yf"])
    source = "yfinance"
    if result is None:
        result = _try_stooq(cfg["stooq"])
        source = "stooq"

    if result is None:
        return Quote(key=key, label=label, error="No data from yfinance or Stooq (both sources unreachable or symbol invalid).")

    last, prev_close, as_of = result
    change_pct = ((last - prev_close) / prev_close * 100.0) if prev_close else None
    return Quote(
        key=key, label=label, last=last, prev_close=prev_close,
        change_pct=change_pct, as_of=as_of, source=source,
    )


def fetch_all_quotes() -> dict[str, Quote]:
    return {key: fetch_quote(key) for key in TICKERS}


@dataclass
class BreakoutInfo:
    key: str
    label: str
    lookback_days: int
    current: Optional[float] = None
    period_high: Optional[float] = None
    period_low: Optional[float] = None
    breakout: Optional[str] = None  # "up", "down", or None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.current is not None and self.period_high is not None


def fetch_breakout(key: str, lookback_days: int = BREAKOUT_LOOKBACK_DAYS) -> BreakoutInfo:
    """
    Flags when the latest close is at or beyond the highest high / lowest low
    of the trailing `lookback_days` trading days -- a simple, well-known
    breakout definition. Requires yfinance (Stooq's quote endpoint doesn't
    give enough daily history for this cheaply, so no Stooq fallback here;
    the report just notes it as unavailable if yfinance can't be reached).
    """
    cfg = TICKERS[key]
    label = cfg["label"]
    try:
        import yfinance as yf
    except ImportError:
        return BreakoutInfo(key=key, label=label, lookback_days=lookback_days, error="yfinance not installed.")

    try:
        ticker = yf.Ticker(cfg["yf"])
        # pad the window so we have a full lookback_days even with holidays/gaps
        hist = ticker.history(period=f"{lookback_days + 15}d", interval="1d")
        if hist is None or hist.empty or len(hist) < 2:
            return BreakoutInfo(key=key, label=label, lookback_days=lookback_days, error="Insufficient price history for breakout calc.")

        window = hist.tail(lookback_days)
        current = float(hist.iloc[-1]["Close"])
        period_high = float(window["High"].max())
        period_low = float(window["Low"].min())

        breakout = None
        if current >= period_high:
            breakout = "up"
        elif current <= period_low:
            breakout = "down"

        return BreakoutInfo(
            key=key, label=label, lookback_days=lookback_days,
            current=current, period_high=period_high, period_low=period_low,
            breakout=breakout,
        )
    except Exception as exc:
        log.debug("breakout fetch failed for %s: %s", key, exc)
        return BreakoutInfo(key=key, label=label, lookback_days=lookback_days, error="Breakout data unreachable (yfinance failed or symbol invalid).")


def fetch_all_breakouts(keys: list[str]) -> dict[str, BreakoutInfo]:
    return {key: fetch_breakout(key) for key in keys}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    quotes = fetch_all_quotes()
    for k, q in quotes.items():
        if q.ok:
            print(f"{q.label:45s} {q.last:>12.3f}  ({q.change_pct:+.2f}%)  via {q.source}")
        else:
            print(f"{q.label:45s} FAILED -- {q.error}")
