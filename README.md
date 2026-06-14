# Daily Article Agent

Sends one curated article per day to your inbox, focused on data science, AI solutions engineering, and modern tech stacks.

## What it does

1. **Discovers** recent articles from arXiv, Hacker News, and curated RSS feeds
2. **Filters** out articles you've already received
3. **Curates** the best pick using OpenAI based on your interests in `config/interests.yaml`
4. **Emails** you a summary with "why it matters" bullets via Gmail

## Quick start

### 1. Install

```bash
cd C:\dev\retrieve_articles
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### 2. Configure secrets

Copy the example env file and fill in your values:

```bash
copy .env.example .env
```

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GMAIL_ADDRESS` | Gmail address used to send |
| `GMAIL_APP_PASSWORD` | [Gmail app password](https://myaccount.google.com/apppasswords) (requires 2FA) |
| `RECIPIENT_EMAIL` | Where to send (defaults to `GMAIL_ADDRESS`) |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for curation |
| `LOOKBACK_DAYS` | `3` | How far back to search |
| `MAX_CANDIDATES` | `50` | Max candidates sent to the agent |

### 3. Customize interests

Edit [`config/interests.yaml`](config/interests.yaml) with your topics, things to avoid, career context, and optional RSS feeds.

### 4. Test locally

```bash
# Discover + curate without sending email or updating history
python -m retrieve_articles --dry-run

# Verify Gmail SMTP works
python -m retrieve_articles --test-email

# Full run (sends email and updates history)
python -m retrieve_articles
```

## Scheduling

### Option A: GitHub Actions (recommended)

Runs on weekdays at 16:00 UTC (~11:00 AM US Eastern during standard time) without needing your PC on.

1. Push this repo to GitHub
2. Add repository secrets:
   - `OPENAI_API_KEY`
   - `GMAIL_ADDRESS`
   - `GMAIL_APP_PASSWORD`
   - `RECIPIENT_EMAIL` (optional if same as Gmail)
3. Enable Actions in the repo settings
4. The workflow at [`.github/workflows/daily-article.yml`](.github/workflows/daily-article.yml) will run on schedule

You can also trigger a manual run from the Actions tab (`workflow_dispatch`).

**DST note:** GitHub cron uses UTC and does not adjust for daylight saving. Update the cron hour in the workflow twice a year, or accept a one-hour shift.

After each successful run, the workflow commits updated `data/seen_articles.json` so duplicates are avoided.

### Option B: Windows Task Scheduler

1. Complete local setup above (venv, `.env`, `pip install -e .`)
2. Open Task Scheduler → Create Basic Task
3. Trigger: Daily, set your preferred time (e.g. 10:30 AM before lunch)
4. Action: Start a program
   - Program: `C:\dev\retrieve_articles\.venv\Scripts\python.exe`
   - Arguments: `-m retrieve_articles`
   - Start in: `C:\dev\retrieve_articles`
5. Ensure the task runs whether or not you're logged in (if desired)

## Project structure

```
retrieve_articles/
├── config/interests.yaml       # Your topics and RSS feeds
├── data/seen_articles.json     # Sent article history
├── src/retrieve_articles/
│   ├── discover/               # arXiv, HN, RSS sources
│   ├── agent.py                # OpenAI selection + summary
│   ├── emailer.py              # Gmail HTML email
│   └── main.py                 # CLI entry point
└── .github/workflows/          # Scheduled CI job
```

## CLI reference

```bash
python -m retrieve_articles              # Full daily run
python -m retrieve_articles --dry-run    # Preview without sending
python -m retrieve_articles --test-email # Send test email
```

## Cost estimate

One `gpt-4o-mini` completion per day is roughly **$0.01–0.05/day**.

## Troubleshooting

**Gmail auth fails:** Ensure 2FA is enabled and you're using an app password, not your regular Gmail password.

**No candidates found:** Increase `LOOKBACK_DAYS` or add more RSS feeds in `config/interests.yaml`.

**OpenAI quota / 429 error:** Your API key has no billing credits. Add a payment method at https://platform.openai.com/settings/organization/billing. Until then, test with:

```bash
python -m retrieve_articles --dry-run --no-llm
```

This skips OpenAI and picks an article by keyword match against your interests.

**GitHub Actions push fails:** Ensure the workflow has `contents: write` permission (already set in the workflow file).
