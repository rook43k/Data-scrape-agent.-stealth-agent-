# XAUUSD Fundamentals Tracker -- Setup Guide

A script you run yourself that pulls the live data that actually drives
gold (XAUUSD) -- price action, the dollar, real yields, oil, risk
sentiment, and optionally headlines -- and pushes a readable briefing to
your phone via Telegram.

It works with **zero API keys** using free, keyless sources (Yahoo Finance
via `yfinance`, with Stooq as an automatic fallback if Yahoo is
unreachable). Two free optional keys make it significantly better:
**FRED** (for real yields -- gold's single most reliable fundamental
driver) and **NewsAPI** (for headline context). Telegram needs a free bot
token if you want push delivery.

---

## 1. Install

```bash
cd xau_fundamentals
pip install -r requirements.txt
```

(If you're on a system that requires it: `pip install -r requirements.txt --break-system-packages`)

## 2. Verify the install before touching real data

```bash
python main.py --self-test
```

This checks your config and imports without making any network calls. It
should print "Self-test passed." If it doesn't, fix what it flags before
continuing -- almost always a missing `pip install`.

## 3. Try it with zero configuration

```bash
python main.py --no-send
```

This pulls live market data (gold, DXY, yields, oil, VIX, S&P 500) from
Yahoo Finance / Stooq -- no keys needed -- and prints a full report to your
terminal. The FRED and headlines sections will say "skipped (optional)"
until you add those keys in step 4. This is normal and expected.

## 4. (Optional but recommended) Add the free keys

Copy the example env file:

```bash
cp .env.example .env
```

Then open `.env` in any text editor and fill in:

### FRED_API_KEY (real yields -- the most important optional upgrade)
1. Go to https://fred.stlouisfed.org/docs/api/api_key.html
2. Create a free account (just email + password) and request a key
3. It's issued instantly -- paste it into `.env` as `FRED_API_KEY=...`

### NEWSAPI_KEY (headline context)
1. Go to https://newsapi.org/register
2. Sign up with email (free tier: 100 requests/day, plenty for this)
3. Copy your key into `.env` as `NEWSAPI_KEY=...`

## 5. Set up Telegram delivery (the actual "push to me" part)

This takes about 2 minutes.

1. **Create your bot.** In Telegram, search for **@BotFather** and start a
   chat. Send it `/newbot`. Follow the prompts (it'll ask for a name and a
   username ending in "bot"). BotFather will reply with a token that looks
   like `123456789:AAH8...`. That's your `TELEGRAM_BOT_TOKEN`.

2. **Start a chat with your new bot.** Search for the bot's username
   (the one you just created) and send it any message, e.g. "hi". Bots
   can't message you first -- this step is required so it's allowed to
   reply to you.

3. **Get your chat ID.** With that "hi" message sent, open this URL in
   your browser (replace `<TOKEN>` with your real token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   You'll see JSON containing `"chat":{"id":NUMBER, ...}`. That `NUMBER`
   (it may be negative) is your `TELEGRAM_CHAT_ID`.

4. **Paste both into `.env`:**
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAH8...
   TELEGRAM_CHAT_ID=987654321
   ```

5. **Test delivery directly:**
   ```bash
   python telegram_delivery.py
   ```
   You should get a "Test message from xau_fundamentals tracker." on
   Telegram within a few seconds. If you get a Telegram API error instead,
   double check the token and chat ID -- the error message will tell you
   what Telegram rejected.

## 6. Run it for real

```bash
python main.py
```

This fetches everything, prints the report, and pushes it to Telegram.

Useful flags:
- `--no-send` -- print/save only, skip the Telegram push
- `--save` -- also write a timestamped `.txt` copy into `./reports/`
- `--self-test` -- sanity-check setup without hitting the network

## What you get in the report

- **Market snapshot**: gold futures, DXY, 10Y nominal yield, WTI crude,
  VIX, S&P 500, and GLD (as a gold-ETF-flow proxy) -- each with last price,
  % change, and which source served it.
- **Rates & inflation** (needs `FRED_API_KEY`): 10Y real yield (TIPS), 10Y
  breakeven inflation, effective Fed funds rate, and CPI year-over-year.
  Real yields are gold's most consistent fundamental driver, so this
  section is worth getting the key for.
- **Quick read**: a short, mechanical check of the textbook gold
  relationships (gold vs. dollar, real yields, risk sentiment) against
  what the data actually shows right now. This is a structured summary of
  directional signals, not a forecast, and the report says so explicitly.
- **Headlines** (needs `NEWSAPI_KEY`): recent gold/Fed/geopolitics
  headlines for qualitative context that price data alone won't capture.

## On scheduling

You said you'd run this manually for now -- just re-run `python main.py`
whenever you want a fresh read. If you later want it automatic:
- **Mac/Linux**: add a cron line, e.g. `0 13 * * 1-5 cd /path/to/xau_fundamentals && python3 main.py >> cron.log 2>&1` (runs weekdays at 13:00)
- **Windows**: use Task Scheduler to run `python main.py` on whatever
  schedule you want.

## Honest limitations

- **Yahoo Finance / Stooq are free and unofficial.** They occasionally
  rate-limit or change behavior without notice. The script automatically
  falls back from Yahoo to Stooq, and clearly labels any data it
  couldn't get rather than guessing -- but on a bad day a field or two may
  read "UNAVAILABLE." That's the trade-off for using zero-cost sources.
- **No CME FedWatch-style rate-hike-odds feed is included.** There's no
  good free, keyless API for that; it would need a paid data vendor or a
  fragile scraper. The Fed funds rate from FRED gives you the current
  rate, not market-implied odds of the next move.
- **This is not financial advice and isn't a trading signal generator.**
  It assembles real data and applies basic textbook relationships (dollar
  vs. gold, real yields vs. gold) as a structured summary -- it doesn't
  predict price direction.
