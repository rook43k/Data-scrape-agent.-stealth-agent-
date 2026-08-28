"""
Configuration for the XAUUSD Fundamentals Tracker.

All sensitive values (API keys, bot tokens) are read from environment
variables so nothing secret ever has to live in this file or get committed
to version control. Copy .env.example to .env and fill in what you have --
everything is optional except you need at least one delivery channel
configured if you want pushes (otherwise it just prints to console).
"""

import os
from pathlib import Path

# ---- load .env if present (no extra dependency needed) ----
def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

_j_dotenv()

# ---- Optional API keys / tokens (all None if not set) ----
FRED_API_KEY = os.environ.get("FRED_API_KEY") or None
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY") or None
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or None
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or None
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL") or None
SMTP_HOST = os.environ.get("SMTP_HOST") or None
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER") or None
SMTP_PASS = os.environ.get("SMTP_PASS") or None
EMAIL_TO = os.environ.get("EMAIL_TO") or None

# ---- Market data tickers (Yahoo Finance symbols, with Stooq fallback symbols) ----
TICKERS = {
    "gold_spot": {"yf": "GC=F", "stooq": "xauusd", "label": "Gold futures (COMEX, front month)"},
    "dxy": {"yf": "DX-Y.NYB", "stooq": "usdx.f", "label": "US Dollar Index (DXY)"},
    "us10y_nominal": {"yf": "^TNX", "stooq": "10usy.b", "label": "US 10Y Treasury yield (nominal)"},
    "wti_crude": {"yf": "CL=F", "stooq": "cl.f", "label": "WTI Crude Oil"},
    "vix": {"yf": "^VIX", "stooq": "vix.f", "label": "CBOE Volatility Index (VIX)"},
    "spx": {"yf": "^GSPC", "stooq": "^spx", "label": "S&P 500"},
    "gld_etf": {"yf": "GLD", "stooq": "gld.us", "label": "SPDR Gold Shares ETF (flow proxy)"},
    "silver_spot": {"yf": "SI=F", "stooq": "xagusd", "label": "Silver futures (COMEX, front month)"},
    "us05y_nominal": {"yf": "^FVX", "stooq": "5usy.b", "label": "US 5Y Treasury yield (nominal)"},
}

# ---- Breakout watch: flag when price crosses its N-day high/low ----
BREAKOUT_LOOKBACK_DAYS = 20
BREAKOUT_TICKERS = ["gold_spot"]

# ---- CFTC Commitment of Traders (COT) -- free, public, no key needed ----
# Disaggregated Futures Only report. Tracks "Managed Money" net positioning,
# the closest free proxy for institutional/hedge-fund positioning in gold.
COT_DATASET_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
COT_CONTRACT_CODE = "088691"  # GOLD - COMMODITY EXCHANGE INC.

# ---- FRED series (only used if FRED_API_KEY is set) ----
FRED_SERIES = {
    "real_yield_10y": {"id": "DFII10", "label": "US 10Y real yield (TIPS)"},
    "breakeven_10y": {"id": "T10YIE", "label": "US 10Y breakeven inflation"},
    "fed_funds_rate": {"id": "DFF", "label": "Effective Fed Funds Rate"},
    "cpi_yoy": {"id": "CPIAUCSL", "label": "CPI (index, for YoY calc)"},
}

# ---- News query (only used if NEWSAPI_KEY is set) ----
NEWS_QUERY = "gold OR XAUUSD OR \"Federal Reserve\" OR \"interest rates\" OR geopolitics"
NEWS_PAGE_SIZE = 8

# ---- Output ----
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./reports"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT = 12  # seconds, applied to all outbound HTTP calls
USER_AGENT = "Mozilla/5.0 (compatible; xau-fundamentals-tracker/1.0)"
