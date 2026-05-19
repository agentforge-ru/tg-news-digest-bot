"""Telegram Bot API delivery."""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from .digest import DigestItem

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


def _format_digest(items: list[DigestItem], header: str | None = None) -> str:
    header = header or f"🗞️ Daily Digest — {datetime.now().strftime('%B %d')}"
    lines = [f"*{header}*", ""]
    for i, item in enumerate(items, start=1):
        lines.append(f"*{i}. {_escape(item.title)}*")
        if item.summary:
            lines.append(item.summary)
        lines.append(f"↪ [{_escape(item.source)}]({item.link})")
        lines.append("")
    return "\n".join(lines).strip()


def _escape(text: str) -> str:
    # MarkdownV2 has more escapes, but classic Markdown is forgiving enough here.
    return text.replace("*", "·").replace("_", " ").replace("[", "(").replace("]", ")")


def send_digest(
    items: list[DigestItem],
    *,
    bot_token: str,
    chat_id: str | int,
    header: str | None = None,
) -> None:
    if not items:
        logger.warning("Nothing to send: empty digest")
        return

    text = _format_digest(items, header=header)
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 50] + "\n\n... (truncated)"

    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    with httpx.Client(timeout=30) as client:
        response = client.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
        )
        response.raise_for_status()
    logger.info("Sent digest with %d items to chat %s", len(items), chat_id)
