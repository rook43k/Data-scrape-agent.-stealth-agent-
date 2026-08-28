"""
Builds a human-readable fundamentals briefing from whatever data sources
succeeded. This is deliberately defensive: every section checks what data
it actually has and says so explicitly rather than presenting gaps as zeros
or silently omitting them.
"""

from __future__ import annotations
from datetime import datetime, timezone

from market_data import Quote, BreakoutInfo
from fred_data import FredPoint
from cot_data import CotPoint


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _fmt_num(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{decimals}f}"


def _direction_arrow(value: float | None) -> str:
    if value is None:
        return ""
    if value > 0.02:
        return "up"
    if value < -0.02:
        return "down"
    return "flat"


def build_market_section(quotes: dict[str, Quote]) -> str:
    lines = ["MARKET SNAPSHOT", "-" * 40]
    for key in ["gold_spot", "silver_spot", "dxy", "us10y_nominal", "us05y_nominal", "wti_crude", "vix", "spx", "gld_etf"]:
        q = quotes.get(key)
        if q is None or not q.ok:
            err = q.error if q else "not fetched"
            lines.append(f"  {key:16s} UNAVAILABLE ({err})")
            continue
        lines.append(
            f"  {q.label:38s} {_fmt_num(q.last):>12s}  {_fmt_pct(q.change_pct):>8s}  [{q.source}, as of {q.as_of[:16] if q.as_of else 'n/a'}]"
        )

    gold = quotes.get("gold_spot")
    silver = quotes.get("silver_spot")
    if gold and gold.ok and silver and silver.ok and silver.last:
        ratio = gold.last / silver.last
        lines.append(f"  {'Gold/Silver ratio':38s} {ratio:>12.2f}")

    us10y = quotes.get("us10y_nominal")
    us05y = quotes.get("us05y_nominal")
    if us10y and us10y.ok and us05y and us05y.ok:
        spread = us10y.last - us05y.last
        lines.append(f"  {'10Y-5Y Treasury spread (curve)':38s} {spread:>+12.2f}")

    return "\n".join(lines)


def build_institutional_section(cot: CotPoint) -> str:
    lines = ["INSTITUTIONAL POSITIONING (CFTC COT, Managed Money)", "-" * 40]
    if not cot.ok:
        lines.append(f"  {cot.error or 'COT data unavailable.'}")
        lines.append("  Source: CFTC Disaggregated Futures Only report (free, weekly, no key needed).")
        return "\n".join(lines)

    lines.append(f"  Report date: {cot.report_date} (CFTC publishes Fridays, ~3-8 days lagged)")
    lines.append(f"  Managed Money net position: {cot.managed_money_net:+,} contracts")
    lines.append(f"  Long: {cot.managed_money_long:,}   Short: {cot.managed_money_short:,}")
    lines.append(f"  Week-over-week change (net): {cot.change_net:+,} contracts")
    lines.append(f"  Total open interest: {cot.open_interest:,} contracts")
    if cot.change_net > 0:
        lines.append("  Managed Money added to net length last week -- speculative positioning leaning more bullish.")
    elif cot.change_net < 0:
        lines.append("  Managed Money reduced net length last week -- speculative positioning leaning less bullish.")
    return "\n".join(lines)


def build_breakout_section(breakouts: dict[str, BreakoutInfo]) -> str:
    lines = ["BREAKOUT WATCH", "-" * 40]
    if not breakouts:
        lines.append("  No breakout data configured.")
        return "\n".join(lines)

    for key, b in breakouts.items():
        if not b.ok:
            lines.append(f"  {b.label:38s} UNAVAILABLE ({b.error})")
            continue
        status = "no breakout"
        if b.breakout == "up":
            status = f"BREAKOUT UP -- at/above {b.lookback_days}-day high"
        elif b.breakout == "down":
            status = f"BREAKOUT DOWN -- at/below {b.lookback_days}-day low"
        lines.append(f"  {b.label:38s} {status}")
        lines.append(f"    current: {_fmt_num(b.current)}   {b.lookback_days}d high: {_fmt_num(b.period_high)}   {b.lookback_days}d low: {_fmt_num(b.period_low)}")
    return "\n".join(lines)


def build_macro_section(fred_points: dict[str, FredPoint], cpi_yoy: float | None) -> str:
    lines = ["RATES & INFLATION (FRED)", "-" * 40]
    any_data = any(p.ok for p in fred_points.values())
    if not any_data:
        lines.append("  All FRED series skipped -- set FRED_API_KEY for real-yield data (free, instant key).")
        lines.append("  Get one at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return "\n".join(lines)

    for key, p in fred_points.items():
        if not p.ok:
            lines.append(f"  {p.label:38s} unavailable ({p.error})")
            continue
        delta = ""
        if p.prev_value is not None:
            d = p.value - p.prev_value
            delta = f"  ({'+' if d >= 0 else ''}{d:.3f} vs prior)"
        lines.append(f"  {p.label:38s} {p.value:>8.3f}  as of {p.date}{delta}")

    if cpi_yoy is not None:
        lines.append(f"  {'CPI YoY (inflation rate)':38s} {cpi_yoy:>7.2f}%")
    return "\n".join(lines)


def build_news_section(headlines, news_error: str | None) -> str:
    lines = ["HEADLINES (qualitative context)", "-" * 40]
    if news_error and not headlines:
        lines.append(f"  {news_error}")
        if "NEWSAPI_KEY not set" in (news_error or ""):
            lines.append("  Get a free key at: https://newsapi.org/register")
        return "\n".join(lines)
    if not headlines:
        lines.append("  No headlines returned.")
        return "\n".join(lines)
    for h in headlines[:8]:
        lines.append(f"  - [{h.source}] {h.title}")
    return "\n".join(lines)


def build_interpretation(quotes: dict[str, Quote], fred_points: dict[str, FredPoint]) -> str:
    """
    A short, mechanical read of the textbook gold relationships against
    whatever data actually came back. This is NOT financial advice and the
    report says so -- it's a structured summary of directional signals,
    not a forecast or recommendation.
    """
    lines = ["QUICK READ (directional signals, not advice)", "-" * 40]

    gold = quotes.get("gold_spot")
    dxy = quotes.get("dxy")
    real_yield = fred_points.get("real_yield_10y")
    vix = quotes.get("vix")

    if gold and gold.ok:
        lines.append(f"  Gold is {_direction_arrow(gold.change_pct)} {_fmt_pct(gold.change_pct)} on the session.")

    if dxy and dxy.ok and gold and gold.ok:
        dxy_dir = _direction_arrow(dxy.change_pct)
        if dxy_dir == "up" and _direction_arrow(gold.change_pct) == "down":
            lines.append("  Dollar strength and gold weakness are moving together -- consistent with the textbook inverse relationship.")
        elif dxy_dir == "down" and _direction_arrow(gold.change_pct) == "up":
            lines.append("  Dollar weakness and gold strength are moving together -- consistent with the textbook inverse relationship.")
        elif dxy_dir != "flat":
            lines.append(f"  DXY is {dxy_dir} ({_fmt_pct(dxy.change_pct)}) while gold's move doesn't mirror it cleanly -- other drivers (yields, risk sentiment) may be dominating today.")

    if real_yield and real_yield.ok:
        lines.append(f"  10Y real yield is at {real_yield.value:.2f}%. Real yields are gold's most consistent fundamental driver: higher real yields raise the opportunity cost of holding non-yielding gold.")
    else:
        lines.append("  Real yield data unavailable -- set FRED_API_KEY to get this, the single highest-signal series for gold.")

    if vix and vix.ok:
        if vix.last > 25:
            lines.append(f"  VIX at {vix.last:.1f} signals elevated market stress -- a backdrop that has historically supported safe-haven demand for gold, though this hasn't been a reliable relationship in every regime.")
        else:
            lines.append(f"  VIX at {vix.last:.1f} is in a calmer range, suggesting limited acute risk-off flow into gold today.")

    return "\n".join(lines)


def build_report(quotes, fred_points, cpi_yoy, headlines, news_error, cot=None, breakouts=None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"XAUUSD FUNDAMENTALS BRIEFING\n"
        f"Generated: {now}\n"
        f"{'=' * 40}\n"
    )
    footer = (
        f"\n{'=' * 40}\n"
        f"Data sources: yfinance/Stooq (price), FRED (rates/inflation, optional), "
        f"NewsAPI (headlines, optional), CFTC (institutional positioning).\n"
        f"This report is informational only and is not financial advice."
    )
    sections = [
        build_market_section(quotes),
        build_macro_section(fred_points, cpi_yoy),
        build_interpretation(quotes, fred_points),
    ]
    if cot is not None:
        sections.append(build_institutional_section(cot))
    if breakouts is not None:
        sections.append(build_breakout_section(breakouts))
    sections.append(build_news_section(headlines, news_error))
    return header + "\n\n".join(sections) + footer
