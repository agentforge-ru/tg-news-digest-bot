"""Entry point. Usage: python -m tg_news_digest --config config.yaml"""
import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .digest import build_digest
from .feeds import deduplicate, fetch_feeds
from .telegram import send_digest


def main() -> None:
    parser = argparse.ArgumentParser(prog="tg-news-digest")
    parser.add_argument("--config", required=True, help="Path to YAML config file.")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout, don't send to Telegram.")
    args = parser.parse_args()

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    log = logging.getLogger("tg-news-digest")

    with open(args.config) as f:
        config = yaml.safe_load(f)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    missing = [
        name
        for name, value in (
            ("TELEGRAM_BOT_TOKEN", bot_token),
            ("TELEGRAM_CHAT_ID", chat_id),
            ("ANTHROPIC_API_KEY", anthropic_key),
        )
        if not value
    ]
    if missing and not args.dry_run:
        print(f"ERROR: missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    log.info("Fetching %d feeds, look_back=%dh", len(config["feeds"]), config["look_back_hours"])
    entries = fetch_feeds(config["feeds"], config["look_back_hours"])
    log.info("Fetched %d entries", len(entries))

    if config.get("deduplication", {}).get("enabled", True):
        threshold = config.get("deduplication", {}).get("similarity_threshold", 0.85)
        entries = deduplicate(entries, threshold=threshold)
        log.info("After dedupe: %d entries", len(entries))

    if not entries:
        log.warning("No fresh entries; skipping")
        return

    log.info("Calling Anthropic to rank + summarize")
    items = build_digest(
        entries,
        top_n=config["top_n"],
        language=config["language"],
        model=config["model"],
        api_key=anthropic_key or "DRY_RUN",
    )
    log.info("Got %d items in digest", len(items))

    if args.dry_run:
        for i, item in enumerate(items, start=1):
            print(f"{i}. {item.title}")
            print(f"   {item.summary}")
            print(f"   {item.link}\n")
        return

    send_digest(items, bot_token=bot_token, chat_id=chat_id)


if __name__ == "__main__":
    main()
