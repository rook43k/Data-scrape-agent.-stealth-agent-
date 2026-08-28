"""
CFTC Commitment of Traders (COT) integration -- Disaggregated Futures Only
report, gold futures (COMEX, contract code 088691).

Free, public, no API key required (CFTC's Socrata "Public Reporting
Environment" API -- see https://publicreporting.cftc.gov). Published every
Friday afternoon, covering positions as of the prior Tuesday, so this data
lags by 3-8 days depending on when you run the script -- that's a property
of the report itself, not a bug here.

Tracks "Managed Money" -- the disaggregated report's speculative/institutional
category (hedge funds, CTAs, commodity pools) -- net long/short positioning
and the week-over-week change, which is one of the most closely watched
positioning signals in the gold market.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from config import COT_DATASET_URL, COT_CONTRACT_CODE, REQUEST_TIMEOUT, USER_AGENT

log = logging.getLogger("xau_fundamentals.cot")


@dataclass
class CotPoint:
    report_date: Optional[str] = None
    managed_money_long: Optional[int] = None
    managed_money_short: Optional[int] = None
    managed_money_net: Optional[int] = None
    change_long: Optional[int] = None
    change_short: Optional[int] = None
    change_net: Optional[int] = None
    open_interest: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.managed_money_net is not None


def _to_int(value, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def fetch_latest_cot() -> CotPoint:
    params = {
        "$where": f"cftc_contract_market_code='{COT_CONTRACT_CODE}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 5,
    }
    try:
        resp = requests.get(
            COT_DATASET_URL, params=params, timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:
        log.debug("CFTC COT fetch failed: %s", exc)
        return CotPoint(error="CFTC COT fetch failed (network or API issue).")

    if not isinstance(rows, list):
        return CotPoint(error="Unexpected response shape from CFTC API.")

    # Defensive client-side filter in case $where isn't honored for any reason.
    rows = [r for r in rows if r.get("cftc_contract_market_code") == COT_CONTRACT_CODE]
    if not rows:
        return CotPoint(error="No COT data returned for gold futures (contract 088691).")

    row = rows[0]
    try:
        long_pos = _to_int(row["m_money_positions_long_all"])
        short_pos = _to_int(row["m_money_positions_short_all"])
        net = long_pos - short_pos
        chg_long = _to_int(row.get("change_in_m_money_long_all"))
        chg_short = _to_int(row.get("change_in_m_money_short_all"))
        chg_net = chg_long - chg_short
        oi = _to_int(row.get("open_interest_all"))
        date = str(row.get("report_date_as_yyyy_mm_dd", ""))[:10]
    except KeyError as exc:
        return CotPoint(error=f"Unexpected COT data shape -- missing field {exc}.")

    return CotPoint(
        report_date=date,
        managed_money_long=long_pos,
        managed_money_short=short_pos,
        managed_money_net=net,
        change_long=chg_long,
        change_short=chg_short,
        change_net=chg_net,
        open_interest=oi,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = fetch_latest_cot()
    if p.ok:
        print(f"Managed Money net: {p.managed_money_net:+,} (as of {p.report_date})")
        print(f"Week-over-week change: {p.change_net:+,}")
        print(f"Open interest: {p.open_interest:,}")
    else:
        print(f"COT data unavailable: {p.error}")
