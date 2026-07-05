# jobindex-scraper

[![CI](https://github.com/sdysch/jobindex_scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/sdysch/jobindex_scraper/actions/workflows/ci.yml)
[![Scrape](https://github.com/sdysch/jobindex_scraper/actions/workflows/scrape.yml/badge.svg)](https://github.com/sdysch/jobindex_scraper/actions/workflows/scrape.yml)
[![Classify](https://github.com/sdysch/jobindex_scraper/actions/workflows/classify.yml/badge.svg)](https://github.com/sdysch/jobindex_scraper/actions/workflows/classify.yml)
[![Notify](https://github.com/sdysch/jobindex_scraper/actions/workflows/notify.yml/badge.svg)](https://github.com/sdysch/jobindex_scraper/actions/workflows/notify.yml)
![Last scrape](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/sdysch/jobindex_scraper/main/last_scrape.json)

Scrape job listings from [Jobindex.dk](https://www.jobindex.dk) in three phases:

1. **Scrape** — fetch raw job postings into Supabase (run every hour)
2. **Classify** — LLM determines language (EN/DK) and matches against private criteria (run every few hours)
3. **Message** — send a Telegram digest of new matches (run on demand)

## Features

- Scrapes multiple search URLs from Jobindex.dk
- LLM-based language classification (English / Danish) — public prompt, no criteria exposed
- LLM-based matching against private search criteria — stays in `.env`
- Deduplicates postings across runs (by Jobindex external ID)
- Stores raw jobs and match results separately in Supabase
- Sends Telegram summary of new matches

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Supabase project
- A [GitHub token](https://github.com/settings/tokens) for GitHub Models
- A Telegram bot token and chat ID

## Setup

```bash
git clone <repo> && cd jobindex-scraper
uv sync
cp .env.example .env
```

Edit `.env` with your credentials, search URLs, and matching criteria.

Run the SQL migrations against your Supabase database (SQL editor):

1. `db/migrations/001_initial.sql` — creates the `jobs` table
2. `db/migrations/002_matches.sql` — creates the `matches` table

## Usage

Three commands, each runs independently:

```bash
# 1. Scrape — fetches jobs from Jobindex.dk, stores new ones
uv run jobindex-scrape

# 2. Classify — reads unclassified jobs, runs LLM, writes match results
uv run jobindex-classify

# 3. Message — reads new matches, sends Telegram digest, marks as notified
uv run jobindex-message
```

Each command validates only the config it needs:

| Command | Requires |
|---|---|
| `jobindex-scrape` | `SUPABASE_URL`, `SUPABASE_KEY`, `SEARCH_URLS` |
| `jobindex-classify` | Supabase + `GITHUB_TOKEN`, `JOB_CRITERIA` |
| `jobindex-message` | Supabase + `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |

### Typical schedule

```
cron:  jobindex-scrape   →  every hour
cron:  jobindex-classify  →  every 4-6 hours
manual: jobindex-message  →  when you want a digest
```

## How it works

1. **Scrape** fetches each search URL, parses the embedded `Stash` JSON from the Jobindex SPA, and upserts job postings into the `jobs` table. Jobs are deduplicated by `external_id`.
2. **Classify** queries jobs without a corresponding `matches` row, sends each to an LLM (GitHub Models / OpenAI-compatible) for language classification and criteria matching, then inserts results into `matches`.
3. **Message** reads `matches` with `notified = false` and `is_match = true`, sends a formatted Telegram message, then marks them as notified.

## Project structure

```
src/jobindex_scraper/
├── __init__.py           # package version
├── __main__.py           # python -m → scrape
├── config.py             # .env config loading
├── scraper.py            # Jobindex.dk HTML + Stash JSON parser
├── database.py           # Supabase client (jobs + matches tables)
├── classifier.py         # LLM classifier (language + criteria)
├── notifier.py           # Telegram bot
├── scrape_cli.py         # scrape entry point
├── classify_cli.py       # classify entry point
└── message_cli.py        # message entry point
db/migrations/
├── 001_initial.sql       # jobs table
└── 002_matches.sql       # matches table
```

## Database schema

- **`jobs`** — raw postings from Jobindex. `external_id` is unique (dedup key).
- **`matches`** — classification results linked to `jobs(id)`. Tracks language, match status, reason, criteria used, and notification state.
