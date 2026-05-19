"""AI-powered ranking and summarization via Anthropic API."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from anthropic import Anthropic

from .feeds import Entry

logger = logging.getLogger(__name__)


@dataclass
class DigestItem:
    title: str
    summary: str
    link: str
    source: str


SYSTEM_PROMPT = """You are a news editor. Given a list of recent articles,
pick the {top_n} most important and impactful ones.

"Important" means: high-impact (affects many people, large markets, key
decisions), novel (not just a re-hash of yesterday's news), substantive (real
information, not pure opinion).

For each picked article, write a tight {language}-language summary in 1-2 sentences.
Don't editorialize. State what happened, who's involved, why it matters.

Respond with strict JSON only:
{{
  "selected": [
    {{"index": <int>, "summary": "<your 1-2 sentence summary in {language}>"}},
    ...
  ]
}}

The "index" refers to the position in the input list (1-based). Output exactly {top_n} items.
"""


def _build_user_prompt(entries: list[Entry]) -> str:
    lines = []
    for i, e in enumerate(entries, start=1):
        body = e.summary[:300] if e.summary else "(no summary in feed)"
        lines.append(f"{i}. [{e.source}] {e.title}\n   {body}\n   {e.link}")
    return "Articles to choose from:\n\n" + "\n\n".join(lines)


def _extract_json(text: str) -> dict:
    # Tolerant of leading/trailing whitespace, markdown fences, etc.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:500]}")
    return json.loads(match.group(0))


def build_digest(
    entries: list[Entry],
    *,
    top_n: int,
    language: str,
    model: str,
    api_key: str,
) -> list[DigestItem]:
    if not entries:
        return []

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT.format(top_n=top_n, language=language),
        messages=[{"role": "user", "content": _build_user_prompt(entries)}],
    )

    text = "".join(block.text for block in response.content if hasattr(block, "text"))
    data = _extract_json(text)

    out: list[DigestItem] = []
    for sel in data.get("selected", [])[:top_n]:
        idx = sel.get("index")
        if not isinstance(idx, int) or idx < 1 or idx > len(entries):
            logger.warning("Skipping invalid index in response: %r", sel)
            continue
        entry = entries[idx - 1]
        out.append(
            DigestItem(
                title=entry.title,
                summary=sel.get("summary", "").strip(),
                link=entry.link,
                source=entry.source,
            )
        )
    return out
