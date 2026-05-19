# tg-news-digest

[![CI](https://github.com/agentforge-ru/tg-news-digest-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/agentforge-ru/tg-news-digest-bot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A minimal **AI-powered news digest for Telegram** — pulls RSS feeds, asks Claude to rank and summarize the most important stories, posts a clean digest to your channel/chat on schedule.

> Stop drowning in news. Run this on a cron — every morning you get the 3-5 stories that actually matter, summarized in 2 sentences each.

---

## 🇷🇺 На русском

**Кому это подойдёт:**
- У тебя **много источников новостей/каналов** и ты тонешь в потоке — хочешь утренний дайджест с топ-3-5 главного
- Ты **контент-мейкер / эксперт** и хочешь автоматизировать reposting релевантного контента в свой Telegram-канал
- Ты **HR / рекрутер / аналитик** и тебе нужен **AI-фильтр** для входящего потока (вакансий, новостей, лидов)

**Что внутри:** Python-скрипт на ~600 строк (feeds + digest + telegram модули), интеграция с Anthropic Claude API, дедупликация дубликатов между источниками, готовый config с примерами фидов, docker-compose для деплоя в одну команду.

**Reference implementation подойдёт как есть для:** AI-дайджестов новостей, фильтрации вакансий, мониторинга мнений в каналах.

**Заказать кастомную версию** (под твой конкретный use case: парсер вакансий с HH, AI-ответы на типовые вопросы клиентов, мониторинг конкурентов и т.д.): [Kwork → agentforge_ru](https://kwork.ru/user/agentforge_ru) — от 2 500 ₽, сроки 48-96 часов.

---

## What it does

```
[ RSS feeds ]  →  [ Fetch + dedupe ]  →  [ Claude ranks + summarizes ]  →  [ Telegram post ]
   (configured by you)                       (top N, in your language)         (your chat/channel)
```

Run it manually or schedule via cron / systemd / Windows Task Scheduler / Docker. No database, no state, no server — just a Python script that does one job well.

## Features

- ✅ Read multiple RSS / Atom feeds in one digest
- ✅ Configurable look-back window (last 12h, 24h, 7d, etc.)
- ✅ AI ranking — Claude picks the most important N (you set N)
- ✅ AI summarization — 1-2 sentences per story, in any language
- ✅ Output language configurable (English, Russian, German, etc.)
- ✅ Send to private chat, group chat, or channel
- ✅ Dedupe across feeds (catches the same story posted in multiple sources)

## Installation

```bash
git clone https://github.com/agentforge-ru/tg-news-digest-bot
cd tg-news-digest-bot
pip install -e .
```

## Setup

### 1. Get a Telegram bot token

Open Telegram → message [@BotFather](https://t.me/BotFather):

```
/newbot
> Enter name: My Daily Digest
> Enter username: my_digest_bot
```

BotFather sends you a token like `123456789:ABC-DEF...`. **Save it.**

### 2. Find your target chat ID

For a **personal chat**: message your bot something (say "/start"), then visit
`https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` — find the `"chat":{"id":...}` field.

For a **channel**: add the bot as administrator with "Post messages" permission, then send any message to the channel and check `getUpdates` again. Channel chat IDs are negative numbers like `-1001234567890`.

### 3. Get an Anthropic API key

https://console.anthropic.com → API Keys → Create. Cost per digest (10 feeds, 50 articles, top-5 summarized) is roughly **$0.005** with Claude Haiku 4.5.

### 4. Configure

Copy `.env.example` to `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890
ANTHROPIC_API_KEY=sk-ant-...
```

Copy `examples/config.example.yaml` to `config.yaml` and edit:

```yaml
look_back_hours: 24
top_n: 5
language: ru
model: claude-haiku-4-5

feeds:
  - https://news.ycombinator.com/rss
  - https://www.theverge.com/rss/index.xml
  - https://www.reuters.com/arc/outboundfeeds/v3/category/technology/?outputType=xml
  - https://habr.com/ru/rss/all/
```

### 5. Run once to test

```bash
python -m tg_news_digest --config config.yaml
```

You should get a digest message in your Telegram chat within ~30 seconds.

### 6. Schedule it

**Cron (Linux/macOS):**

```cron
0 8 * * * cd /path/to/tg-news-digest-bot && python -m tg_news_digest --config config.yaml >> /var/log/digest.log 2>&1
```

**Windows Task Scheduler:**

Create a Basic Task → Trigger: Daily 8:00 AM → Action: Start a program → `python` with arguments `-m tg_news_digest --config C:\path\to\config.yaml`.

**Docker:**

```bash
docker compose -f examples/docker-compose.example.yml up -d
```

## Sample output

```
🗞️ Daily Digest — March 15

1. Anthropic releases Claude 4.7 with 1M-token context
   The new model adds a 1M-token context window for the Opus and Sonnet
   tiers, ~5× the previous limit. Available via API today.
   ↪ https://www.anthropic.com/news/...

2. Meta open-sources Llama 4 weights, claims GPT-4 parity
   New 405B-parameter model under a community license. Outperforms
   GPT-4 on 38 of 50 benchmarks but trails on multilingual tasks.
   ↪ https://ai.meta.com/blog/...

3. ECB cuts rates 25bp, signals further easing in Q2
   The European Central Bank reduced its main refinancing rate to 3.25%,
   citing softer inflation data. Markets had priced in 75% probability.
   ↪ https://www.reuters.com/...

... 2 more
```

## Architecture

```
[ feeds.py ]      Fetch RSS feeds, parse entries, filter by date,
       ↓          dedupe by title similarity (>80% match)
[ digest.py ]     Build prompt → call Anthropic API → parse JSON output
       ↓          (top_n entries with summaries)
[ telegram.py ]   Format markdown message → POST to Telegram Bot API
```

Each module is ~80 lines. Easy to fork and adapt.

## Configuration reference

```yaml
look_back_hours: 24      # Only consider entries published within this window
top_n: 5                 # How many to include in the digest
language: en             # Output language (en, ru, de, etc.)
model: claude-haiku-4-5  # Anthropic model id
feeds:                   # List of RSS/Atom URLs
  - https://...
deduplication:
  enabled: true
  similarity_threshold: 0.85  # 0.0-1.0, higher = stricter dedupe
```

## Limitations

- **No interactive bot mode.** This is a fire-and-forget script. If you want `/add_feed` / `/remove_feed` commands, fork it — the building blocks are there.
- **No paywalled article handling.** If a feed only gives titles, summaries will be based on the title alone.
- **No image attachments.** Telegram supports images but I chose to keep posts text-only for readability and rate limits.
- **Anthropic API cost.** Roughly $0.005 / digest with Haiku, $0.02 with Sonnet, $0.10 with Opus. You pay; no recurring cost from this project.

## License

MIT — see `LICENSE`. Use it, fork it, send PRs.

## Author

Built by [agentforge_ru](https://github.com/agentforge-ru) — custom Claude Code subagents, MCP servers, and Telegram bots with AI logic.

Need a custom Telegram-bot with AI logic for your business (lead filtering, customer support, content moderation, etc.)? [Open an issue](https://github.com/agentforge-ru/tg-news-digest-bot/issues) or reach via Kwork.
