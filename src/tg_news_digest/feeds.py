"""RSS / Atom feed fetching and deduplication."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Entry:
    title: str
    summary: str
    link: str
    source: str
    published: datetime


def _coerce_published(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        ts = getattr(entry, attr, None)
        if ts is not None:
            return datetime(*ts[:6], tzinfo=timezone.utc)
    return None


def fetch_feeds(urls: list[str], look_back_hours: int) -> list[Entry]:
    """Fetch all feeds, filter by recency, return flat list of entries."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=look_back_hours)
    out: list[Entry] = []

    for url in urls:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", url, e)
            continue

        source = parsed.feed.get("title", url)
        for entry in parsed.entries:
            published = _coerce_published(entry)
            if published is None or published < cutoff:
                continue
            out.append(
                Entry(
                    title=entry.get("title", "(no title)").strip(),
                    summary=entry.get("summary", "").strip()[:1000],
                    link=entry.get("link", "").strip(),
                    source=source,
                    published=published,
                )
            )

    return out


def deduplicate(entries: list[Entry], threshold: float = 0.85) -> list[Entry]:
    """Remove near-duplicate entries by title similarity. Keeps the earliest of each cluster."""
    if not entries:
        return []

    sorted_entries = sorted(entries, key=lambda e: e.published)
    deduped: list[Entry] = []

    for entry in sorted_entries:
        is_duplicate = False
        for kept in deduped:
            similarity = SequenceMatcher(None, entry.title.lower(), kept.title.lower()).ratio()
            if similarity >= threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            deduped.append(entry)

    return deduped
