# Reddit Newsletter

A Python application that scrapes AI-coding subreddits daily, uses Claude to categorize and synthesize posts, and delivers a newsletter via a web dashboard.

## How It Works

1. **Scrape** — Fetches hot posts + top comments from 6 subreddits using PRAW
2. **Categorize** — Sends posts to Claude Sonnet in batch; gets category, relevance/quality scores, tool tags, summary, and key insight per post
3. **Synthesize** — Sends top-scoring posts grouped by section to Claude; generates edition title, headlines, and blurbs
4. **Display** — Serves the newsletter on a FastAPI web dashboard with client-side filtering

## Newsletter Sections

| Section | Content |
|---|---|
| Top Story | Single most impactful item |
| News & Announcements | Model releases, feature updates |
| Best Practices | Configs, workflows, CLAUDE.md tips |
| Prompts & Techniques | Notable prompts, prompt engineering |
| Tools & Integrations | MCP servers, extensions, plugins |
| Community Highlights | Most discussed posts |
| Quick Links | Honorable mentions (title + one-liner) |

## Subreddits

r/ClaudeAI, r/cursor, r/CopilotCodex, r/ChatGPTCoding, r/LocalLLaMA, r/aicoding

Configurable in `config/subreddits.yaml` — add or remove subreddits without code changes.

## Setup

### Prerequisites

- Python 3.9+
- Reddit API credentials ([register here](https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164))
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configure

```bash
cp .env.example .env
```

Fill in your `.env`:

```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=newsletter-bot/0.1
ANTHROPIC_API_KEY=sk-ant-...
```

### Initialize the database

```bash
alembic upgrade head
```

## Usage

```bash
# Full pipeline: scrape → analyze → synthesize
newsletter pipeline

# Individual steps
newsletter scrape          # Scrape subreddits only
newsletter analyze         # Categorize unprocessed posts only

# Web dashboard
newsletter serve           # Start at http://localhost:8000

# Scheduler (runs pipeline daily at configured time)
newsletter schedule
```

## Web Dashboard

| Route | Description |
|---|---|
| `GET /` | Latest newsletter |
| `GET /newsletter/{id}` | Single edition |
| `GET /archive` | Paginated list of past editions |
| `POST /api/pipeline/run` | Trigger pipeline via API |

The newsletter view includes client-side filtering by subreddit and tool tag (claude_code, copilot, cursor, chatgpt, local_llm, mcp, general).

## Configuration

- **`.env`** — Secrets (Reddit, Anthropic, SMTP)
- **`config/subreddits.yaml`** — Subreddit list, fetch limits, sort order
- **`config/newsletter.yaml`** — Sections, schedule, Claude model settings, post truncation limits

## Docker

```bash
docker compose up -d
```

Runs two services: `web` (dashboard on port 8000) and `scheduler` (daily pipeline).

## Cost

~$0.30–0.45 per pipeline run (2 Claude Sonnet API calls). At daily frequency, ~$9–14/month.

## Project Structure

```
src/newsletter/
├── main.py                  # Typer CLI
├── config.py                # pydantic-settings + YAML loading
├── database.py              # SQLAlchemy engine/session
├── models.py                # 6 ORM tables
├── scraper/reddit.py        # PRAW scraper
├── analyzer/
│   ├── prompts.py           # Prompt templates
│   ├── categorizer.py       # Claude call #1: batch categorization
│   └── synthesizer.py       # Claude call #2: newsletter generation
├── pipeline/orchestrator.py # End-to-end pipeline
├── delivery/
│   ├── scheduler.py         # APScheduler cron
│   └── email.py             # SMTP stub (deferred)
├── web/
│   ├── app.py               # FastAPI routes
│   └── dependencies.py      # DB session injection
├── templates/               # Jinja2 templates
└── static/                  # CSS + JS
```
