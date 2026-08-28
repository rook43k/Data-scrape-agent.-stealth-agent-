"""
Telegram delivery. Requires a free bot token (from @BotFather) and your
chat ID. See SETUP.md for the 2-minute walkthrough.

Telegram messages are capped at 4096 characters -- long reports are split
into multiple messages automatically.
"""

from __future__ import annotations
import logging

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REQUEST_TIMEOUT

log = logging.getLogger("xau_fundamentals.telegram")

TELEGRAM_MAX_LEN = 4000  # leave headroom under the real 4096 cap


def _chunk(text: str, size: int = TELEGRAM_MAX_LEN) -> list[str]:
    chunks = []
    while text:
        if len(text) <= size:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, size)
        if split_at == -1:
            split_at = size
        chunks.append(text[:split_at])
        text = text[split_at:]
    return chunks


def send_telegram(message: str) -> tuple[bool, str]:
    """Returns (success, info_message)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram not configured -- set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    sent = 0
    for chunk in _chunk(message):
        try:
            resp = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "disable_web_page_preview": True},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                return False, f"Telegram API error {resp.status_code}: {resp.text[:200]}"
            sent += 1
        except Exception as exc:
            return False, f"Telegram request failed: {exc}"
    return True, f"Sent {sent} message(s) to Telegram."


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ok, info = send_telegram("Test message from xau_fundamentals tracker.")
    print(("OK: " if ok else "FAILED: ") + info)
