# EOD Auto Reporter

Automated End-of-Day summary generator that pulls activity from **GitHub** and **ClickUp**, formats a clean report, and posts it to **Slack** — every weekday, hands-free.

---

## Features

- Fetches today's GitHub commits and pull requests (opened & merged)
- Fetches today's ClickUp task updates, completions, status changes, and comments
- Generates a professional Slack-formatted EOD summary
- Posts to a Slack channel daily on weekdays via APScheduler
- Skips posting when Slack status is OOO (out-of-office)
- Manual trigger via `POST /trigger-eod`
- Health check at `GET /health`
- Clean architecture with service layer, Pydantic models, and centralized logging
- Ready for Docker / Render / Railway / VPS deployment

---

## Project Structure

```
eod-auto-reporter/
├── app/
│   ├── main.py                  # FastAPI app + startup
│   ├── config.py                # Pydantic BaseSettings
│   ├── logger.py                # Centralized logging
│   ├── scheduler.py             # APScheduler cron job
│   ├── services/
│   │   ├── github_service.py    # GitHub REST API integration
│   │   ├── clickup_service.py   # ClickUp API v2 integration
│   │   ├── slack_service.py     # Slack WebClient integration
│   │   └── summary_service.py   # Report formatter
│   └── models/
│       └── activity_models.py   # Pydantic domain models
├── tests/                       # Unit tests (pytest)
├── .env.example                 # Template for environment variables
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Prerequisites

- Python 3.11+
- A GitHub Personal Access Token
- A ClickUp API Token
- A Slack Bot Token

---

## Setup

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd eod-auto-reporter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all values (see sections below for how to obtain each token).

### 3. Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

The scheduler starts automatically on boot. Visit `http://localhost:8000/health` to verify.

### 4. Run Tests

```bash
pytest tests/ -v
```

---

## How to Get Your Tokens

### GitHub Personal Access Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)** or use fine-grained tokens
3. Select scopes: `repo`, `read:user`
4. Copy the token → set as `GITHUB_TOKEN`
5. Set `GITHUB_USERNAME` to your GitHub login

### ClickUp API Token

1. Open ClickUp → click your avatar (bottom-left) → **Settings**
2. Go to **Apps** in the sidebar
3. Under **API Token**, click **Generate** (or copy existing)
4. Copy the token → set as `CLICKUP_API_TOKEN`

### Finding ClickUp Team ID

1. Open any ClickUp space in your browser
2. The URL looks like: `https://app.clickup.com/12345678/...`
3. The number after `app.clickup.com/` is your **Team ID**
4. Alternatively, call: `curl -H "Authorization: YOUR_TOKEN" https://api.clickup.com/api/v2/team`

### Finding ClickUp User ID

1. Call: `curl -H "Authorization: YOUR_TOKEN" https://api.clickup.com/api/v2/team`
2. In the response, find your user under `team.members[].user`
3. Your numeric `id` field is the **User ID**

### Slack Bot Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name it (e.g. "EOD Reporter") and pick your workspace
4. Go to **OAuth & Permissions** in the sidebar
5. Under **Bot Token Scopes**, add:
   - `chat:write` — to post messages
   - `users.profile:read` — to check OOO status
6. Click **Install to Workspace** and authorize
7. Copy the **Bot User OAuth Token** (`xoxb-...`) → set as `SLACK_BOT_TOKEN`
8. Invite the bot to your channel: `/invite @EOD Reporter`
9. Set `SLACK_CHANNEL` to the channel name (e.g. `#eod-updates`) or channel ID

---

## API Endpoints

| Method | Path           | Description                        |
| ------ | -------------- | ---------------------------------- |
| GET    | `/health`      | Returns status, timestamp, version |
| POST   | `/trigger-eod` | Manually trigger the EOD pipeline  |

### Example: Manual Trigger

```bash
curl -X POST http://localhost:8000/trigger-eod
```

Response:

```json
{
  "status": "accepted",
  "message": "EOD pipeline has been triggered and is running in the background."
}
```

---

## Scheduler Configuration

The report runs automatically **Monday–Friday** at the time you configure:

| Variable        | Default        | Description                |
| --------------- | -------------- | -------------------------- |
| `REPORT_HOUR`   | `18`           | Hour in 24h format         |
| `REPORT_MINUTE` | `0`            | Minute                     |
| `TIMEZONE`      | `Asia/Kolkata` | IANA timezone for schedule |

The scheduler uses APScheduler's `CronTrigger` with `day_of_week='mon-fri'`.

---

## Deployment

### Docker

```bash
docker build -t eod-auto-reporter .
docker run -d --env-file .env -p 8000:8000 eod-auto-reporter
```

### Render

1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect your GitHub repo
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from `.env.example`
6. Deploy

### Railway

1. Create a new project on [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Railway auto-detects the `Dockerfile` or use:
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in the Railway dashboard
5. Deploy

### VPS (systemd)

```bash
# /etc/systemd/system/eod-reporter.service
[Unit]
Description=EOD Auto Reporter
After=network.target

[Service]
User=deploy
WorkingDirectory=/opt/eod-auto-reporter
EnvironmentFile=/opt/eod-auto-reporter/.env
ExecStart=/opt/eod-auto-reporter/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable eod-reporter
sudo systemctl start eod-reporter
```

---

## Example Output

```
📌 EOD Update — Friday, February 13 2026

🚀 Development
Commits
  • abc1234 fix: resolve flaky test  (backend)
  • def5678 feat: add caching layer  (backend)
PRs Merged
  • #42 Add caching layer  (backend)

📋 ClickUp Updates
Completed
  • Write unit tests → done
Status Changes
  • Implement auth → review

✅ Focus Summary
Focused on 2 commits, 1 PR, 1 task completed today.
```

---

## Extending

This project is designed to be extended:

- **AI Summarization**: Replace `_focus_sentence()` in `summary_service.py` with an LLM call (OpenAI, Claude, etc.) for richer summaries
- **Manual Task Entry**: Add a `POST /tasks` endpoint to accept manually logged items and merge them into the daily activity
- **Google Calendar OOO**: Add a calendar check in `scheduler.py` before the OOO guard
- **Multiple Channels**: Support per-team or per-project Slack channels
- **Web Dashboard**: Add a simple frontend to view past reports

---

## License

MIT
