# XAUUSD Fundamentals Tracker

A self-contained Python tool that pulls the live data actually driving
gold (XAUUSD) right now and pushes a readable briefing to your phone via
Telegram. Runs entirely on free sources -- works with zero API keys,
gets better with two free optional ones.

**Start here -> [SETUP.md](./SETUP.md)** for the full walkthrough
(install, free key signup links, Telegram bot setup, all in order).

## What's covered

| Driver | Source | Key needed? |
|---|---|---|
| Gold price, DXY, 10Y yield, oil, VIX, S&P 500, GLD | Yahoo Finance (+ Stooq fallback) | No |
| 10Y real yield, breakeven inflation, Fed funds rate, CPI YoY | FRED | Free, instant |
| Gold/Fed/geopolitics headlines | NewsAPI | Free, instant |
| Delivery | Telegram bot | Free, ~2 min setup |

## Files

```
main.py                # entry point -- run this
config.py               # reads .env, all settings in one place
market_data.py          # price data: yfinance primary, Stooq fallback
fred_data.py             # real yields / inflation / Fed funds (optional)
news_data.py             # headlines (optional)
report.py                # turns raw data into a readable briefing
telegram_delivery.py     # pushes the briefing to Telegram
requirements.txt
.env.example             # copy to .env and fill in your keys
SETUP.md                 # full setup walkthrough -- read this first
```

## Quick start

```bash
pip install -r requirements.txt
python main.py --self-test     # verify setup, no network calls
python main.py --no-send       # try it with live data, no Telegram needed
```

Then follow SETUP.md to add Telegram (and optionally FRED/NewsAPI keys)
for the full experience.

This tool is informational only and is not financial advice.
