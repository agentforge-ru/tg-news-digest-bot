"""Smoke tests for tg_news_digest. Verifies modules import, dedup logic works,
and message formatting produces valid output. Live API calls (Telegram, Anthropic, RSS)
are NOT exercised — CI has no credentials."""
from __future__ import annotations

from datetime import datetime, timezone

from tg_news_digest.digest import DigestItem
from tg_news_digest.feeds import Entry, deduplicate
from tg_news_digest.telegram import _format_digest


def test_package_imports():
    """Package imports without errors."""
    import tg_news_digest

    assert tg_news_digest.__version__


# --- deduplicate ----------------------------------------------------------

def _entry(title: str, hours_ago: int = 1, source: str = "TestSource") -> Entry:
    return Entry(
        title=title,
        summary="",
        link=f"https://example.test/{abs(hash(title))}",
        source=source,
        published=datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0),
    )


def test_dedup_keeps_unique_entries():
    entries = [
        _entry("Anthropic releases Claude 5"),
        _entry("Meta open-sources new model"),
        _entry("ECB cuts rates by 25bp"),
    ]
    result = deduplicate(entries, threshold=0.85)
    assert len(result) == 3


def test_dedup_collapses_near_duplicates():
    entries = [
        _entry("Anthropic releases Claude 5"),
        _entry("Anthropic releases Claude 5.0", source="Mirror"),
        _entry("Meta open-sources new model"),
    ]
    result = deduplicate(entries, threshold=0.85)
    assert len(result) == 2


def test_dedup_handles_empty_input():
    assert deduplicate([], threshold=0.85) == []


# --- telegram message formatting ------------------------------------------

def test_format_digest_produces_message():
    items = [
        DigestItem(
            title="Anthropic ships Claude 5",
            summary="The new model adds tool-use improvements.",
            link="https://example.test/1",
            source="TechBlog",
        ),
        DigestItem(
            title="Meta open-sources Llama 4",
            summary="405B parameter model under community license.",
            link="https://example.test/2",
            source="AI News",
        ),
    ]
    text = _format_digest(items)
    assert "Anthropic ships Claude 5" in text
    assert "Meta open-sources Llama 4" in text
    assert "https://example.test/1" in text


def test_format_digest_handles_empty_summary():
    items = [DigestItem(title="Headline only", summary="", link="https://x.test", source="Src")]
    text = _format_digest(items)
    assert "Headline only" in text
