#!/usr/bin/env python3
"""
XAUUSD Fundamentals Tracker -- main entry point.

Usage:
    python main.py                 # fetch, build report, print + try delivery
    python main.py --no-send       # fetch and print only, skip Telegram push
    python main.py --self-test     # verify config/imports without network calls
    python main.py --save          # also save the report as a timestamped .txt file

Run `python main.py --self-test` first after setup to confirm everything is
wired correctly before relying on real data.
"""

from __future__ import annotations
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import config
from market_data import fetch_all_quotes, fetch_all_breakouts
from fred_data import fetch_all_points, compute_cpi_yoy
from news_data import fetch_headlines
from cot_data import fetch_latest_cot
from report import build_report
from telegram_delivery import send_telegram

log = logging.getLogger("xau_fundamentals.main")


def self_test() -> int:
    """Checks imports, config loading, and module wiring without hitting the network."""
    print("Running self-test (no network calls)...\n")
    issues = []

    print(f"[config]   OUTPUT_DIR resolves to: {config.OUTPUT_DIR.resolve()}")
    print(f"[config]   FRED_API_KEY set:        {'yes' if config.FRED_API_KEY else 'no (optional)'}")
    print(f"[config]   NEWSAPI_KEY set:          {'yes' if config.NEWSAPI_KEY else 'no (optional)'}")
    print(f"[config]   TELEGRAM configured:      {'yes' if (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID) else 'no'}")

    try:
        import yfinance  # noqa: F401
        print("[deps]     yfinance import OK")
    except ImportError:
        issues.append("yfinance is not installed -- run: pip install -r requirements.txt")

    try:
        import requests  # noqa: F401
        print("[deps]     requests import OK")
    except ImportError:
        issues.append("requests is not installed -- run: pip install -r requirements.txt")

    try:
        from report import build_report as _br  # noqa: F401
        from market_data import Quote  # noqa: F401
        from fred_data import FredPoint  # noqa: F401
        dummy_quotes = {"gold_spot": Quote(key="gold_spot", label="test", last=4000.0, prev_close=3990.0, change_pct=0.25, as_of="2026-01-01", source="test")}
        dummy_fred = {"real_yield_10y": FredPoint(key="real_yield_10y", label="test", value=1.8, date="2026-01-01")}
        rendered = _br(dummy_quotes, dummy_fred, None, [], None)
        assert "XAUUSD FUNDAMENTALS BRIEFING" in rendered
        print("[logic]    report builder renders correctly with dummy data")
    except Exception as exc:
        issues.append(f"report builder failed on dummy data: {exc}")

    print()
    if issues:
        print("SELF-TEST FOUND ISSUES:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("Self-test passed. Run without --self-test to pull live data.")
    return 0


def run(send: bool, save: bool) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    print("Fetching market data (yfinance / Stooq)...", file=sys.stderr)
    quotes = fetch_all_quotes()

    print("Fetching FRED macro data (if configured)...", file=sys.stderr)
    fred_points = fetch_all_points()
    cpi_yoy = compute_cpi_yoy(fred_points)

    print("Fetching headlines (if configured)...", file=sys.stderr)
    headlines, news_error = fetch_headlines()

    print("Fetching CFTC institutional positioning (COT)...", file=sys.stderr)
    cot = fetch_latest_cot()

    print("Checking breakout levels...", file=sys.stderr)
    breakouts = fetch_all_breakouts(config.BREAKOUT_TICKERS)

    report_text = build_report(quotes, fred_points, cpi_yoy, headlines, news_error, cot=cot, breakouts=breakouts)
    print("\n" + report_text + "\n")

    if save:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = Path(config.OUTPUT_DIR) / f"xau_report_{ts}.txt"
        out_path.write_text(report_text)
        print(f"Saved report to: {out_path.resolve()}", file=sys.stderr)

    if send:
        ok, info = send_telegram(report_text)
        print(("Telegram: " + info), file=sys.stderr)
        if not ok:
            return 2

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="XAUUSD fundamentals tracker")
    parser.add_argument("--no-send", action="store_true", help="Skip Telegram delivery, just print/save.")
    parser.add_argument("--save", action="store_true", help="Save the report to ./reports as a .txt file.")
    parser.add_argument("--self-test", action="store_true", help="Verify setup without making network calls.")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    return run(send=not args.no_send, save=args.save)


if __name__ == "__main__":
    sys.exit(main())
