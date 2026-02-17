# EOD Auto Reporter — Architecture & Design

This document describes the architecture, components, data flow, and deployment of the EOD Auto Reporter application.

---

## 1. Overview

**EOD Auto Reporter** is a macOS desktop application that automates end-of-day (EOD) summaries. It aggregates daily activity from **GitHub**, **ClickUp**, and **Slack**, optionally enriches it with AI summarization, and posts formatted reports to a Slack channel on a schedule (Mon–Fri) or on demand.

### 1.1 Key Capabilities

| Capability | Description |
|------------|-------------|
| **GitHub** | Fetches commits and PRs (opened & merged) authored today |
| **ClickUp** | Fetches task updates, completions, status changes, and comments |
| **Slack** | Posts EOD reports; checks OOO status; optionally fetches channel discussions |
| **AI Summary** | Optional LLM-based summary (Google Gemini, Groq, OpenAI) |
| **Manual Updates** | User-authored bullet points merged into the report |
| **Scheduling** | Cron-style Mon–Fri at configured time, or "Send EOD Now" |

### 1.2 Deployment Modes

| Mode | Entry Point | Scheduler | Config Source |
|------|-------------|-----------|---------------|
| **Desktop (macOS)** | `desktop/main.py` | `LocalScheduler` (BackgroundScheduler) | `~/Library/Application Support/EOD Reporter/config.json` |
| **Cloud (FastAPI)** | `app/main.py` | `AsyncIOScheduler` | `.env` / environment variables |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EOD Auto Reporter                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌──────────────────────┐                    ┌────────────────────────────────┐ │
│   │   Desktop Layer      │                    │   Core Layer (app/)             │ │
│   │   (desktop/)         │                    │                                 │ │
│   │                      │                    │   ┌──────────────────────────┐  │ │
│   │  ┌────────────────┐  │   Service Bridge   │   │  Scheduler              │  │ │
│   │  │ AppWindow       │  │   (env injection) │   │  (APScheduler)           │  │ │
│   │  │  - Dashboard    │  │◄──────────────────┼───│  - Mon–Fri cron          │  │ │
│   │  │  - Activity     │  │                    │   │  - run_eod_pipeline()    │  │ │
│   │  │  - Settings     │  │                    │   └───────────┬────────────┘  │ │
│   │  │  - Support      │  │                    │               │               │ │
│   │  └────────┬───────┘  │                    │               ▼               │ │
│   │           │          │                    │   ┌──────────────────────────┐  │ │
│   │  ┌────────▼───────┐  │                    │   │  EOD Pipeline            │  │ │
│   │  │ LocalScheduler │  │                    │   │  1. OOO check             │  │ │
│   │  │ (Background)   │  │                    │   │  2. Fetch GitHub/ClickUp  │  │ │
│   │  └────────┬───────┘  │                    │   │  3. Build summary blocks  │  │ │
│   │           │          │                    │   │  4. Post to Slack         │  │ │
│   │  ┌────────▼───────┐  │                    │   └──────────────────────────┘  │ │
│   │  │ ConfigStore    │  │                    │                                 │ │
│   │  │ (JSON persist) │  │                    │   Services:                      │ │
│   │  └────────────────┘  │                    │   github, clickup, slack,       │ │
│   │                      │                    │   slack_activity, ai_summary,  │ │
│   └──────────────────────┘                    │   summary_service              │ │
│                                               └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
         │                              │                              │
         ▼                              ▼                              ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│ GitHub REST API │          │ ClickUp API v2  │          │ Slack Web API   │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Desktop Layer (`desktop/`)

| Module | Responsibility |
|--------|----------------|
| **main.py** | Entry point; ensures project root on `sys.path`; loads config; injects env; launches CustomTkinter GUI |
| **app_window.py** | Root window; sidebar nav; view switching; scheduler lifecycle; theme toggle |
| **config_store.py** | Persists config as JSON; base64-encodes tokens; imports from `.env`; platform-specific paths |
| **service_bridge.py** | Maps config keys → env vars; `init_env_from_config()`; `reload_services()` for hot-reload |
| **local_scheduler.py** | `BackgroundScheduler`; runs EOD pipeline in thread; status callbacks for UI |
| **utils.py** | UI helpers (scrollable frames, mousewheel binding) |

#### Views (`desktop/views/`)

| View | Purpose |
|------|---------|
| **DashboardView** | Stats overview; "Send EOD Now"; "Refresh Stats"; next run time; scheduler status |
| **ActivityView** | Today's activity feed; filters (GitHub/ClickUp/Slack/Manual); manual updates editor; Send EOD |
| **SettingsView** | Token inputs; API tests; schedule config; AI provider settings |
| **SupportView** | Docs, links, config path |

### 3.2 Core Layer (`app/`)

| Module | Responsibility |
|--------|----------------|
| **config.py** | Pydantic `Settings`; loads from env; singleton `settings` |
| **logger.py** | Centralized logging |
| **scheduler.py** | `AsyncIOScheduler`; `run_eod_pipeline()`; cron Mon–Fri; manual updates from config_store |
| **main.py** | FastAPI app; `/health`, `/trigger-eod`; lifespan starts/stops scheduler |

### 3.3 Services (`app/services/`)

| Service | API | Output |
|---------|-----|--------|
| **github_service** | GitHub REST v3 | `GitHubActivity` (commits, prs_opened, prs_merged) |
| **clickup_service** | ClickUp API v2 | `ClickUpActivity` (tasks_updated, tasks_completed, status_changes, comments) |
| **slack_service** | Slack Web API | `send_message()`, `is_user_ooo()`, identity resolution |
| **slack_activity_service** | Slack Web API | `SlackChannelActivity` (messages from monitored channels) |
| **ai_summary_service** | OpenAI-compatible | `AISummary` (optional LLM digest) |
| **summary_service** | — | `generate_summary_blocks()`, `generate_summary()` → Slack Block Kit |

### 3.4 Models (`app/models/`)

| Model | Description |
|-------|-------------|
| **GitHubCommit** | sha, message, repo, url, timestamp |
| **GitHubPR** | number, title, repo, state, url, created_at, merged_at |
| **GitHubActivity** | commits, prs_opened, prs_merged |
| **ClickUpTask** | task_id, name, status, previous_status, parent_id, url, date_updated |
| **ClickUpComment** | task_id, task_name, comment_text, date |
| **ClickUpActivity** | tasks_updated, tasks_completed, status_changes, comments |
| **SlackMessage** | user_id, user_name, text, channel_id, channel_name, timestamp |
| **SlackChannelActivity** | messages |
| **AISummary** | summary_text, generated_at |
| **DailyActivity** | date, github, clickup, slack_discussions, manual_updates, ai_summary |

---

## 4. Data Flow

### 4.1 EOD Pipeline (Scheduled or Manual)

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    run_eod_pipeline()                        │
                    └─────────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
            ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
            │ OOO Check     │         │ Fetch GitHub  │         │ Fetch ClickUp │
            │ (Slack)       │         │ Activity      │         │ Activity      │
            └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
                    │                         │                         │
                    │ skip if OOO             │                         │
                    │                         └────────────┬────────────┘
                    │                                      │
                    │                         ┌────────────▼────────────┐
                    │                         │ Load manual_updates      │
                    │                         │ from config_store        │
                    │                         └────────────┬────────────┘
                    │                                      │
                    │                         ┌────────────▼────────────┐
                    │                         │ DailyActivity           │
                    │                         │ (github, clickup,       │
                    │                         │  manual_updates)        │
                    │                         └────────────┬────────────┘
                    │                                      │
                    │                         ┌────────────▼────────────┐
                    │                         │ summary_service        │
                    │                         │ generate_summary_blocks │
                    │                         │ generate_summary        │
                    │                         └────────────┬────────────┘
                    │                                      │
                    │                         ┌────────────▼────────────┐
                    └────────────────────────►│ slack_service          │
                                             │ send_message(channel,   │
                                             │   text, blocks)         │
                                             └────────────────────────┘
```

### 4.2 Desktop Config → Core Services

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  User edits Settings → save_config() → config.json                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  apply_config_and_reload()                                                   │
│  1. init_env_from_config() → os.environ[GITHUB_TOKEN] = ...                  │
│  2. reload_services() → importlib.reload(app.config, app.services.*)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Pydantic Settings() re-reads env; module-level _HEADERS, _client re-init     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Activity View Refresh (Desktop)

```
ActivityView._refresh()
        │
        ├── github_service.fetch_github_activity()
        ├── clickup_service.fetch_clickup_activity()
        ├── slack_activity_service.fetch_slack_channel_activity(monitor_channels)
        └── (optional) ai_summary_service.generate_ai_summary(...)
        │
        ▼
Render cards: GitHub, ClickUp, Slack, Manual
```

---

## 5. Configuration

### 5.1 Config Store (Desktop)

| Location | Path |
|----------|------|
| **macOS** | `~/Library/Application Support/EOD Reporter/config.json` |
| **Windows** | `%APPDATA%/EOD Reporter/config.json` |
| **Linux** | `~/.config/EOD Reporter/config.json` |

Sensitive fields (`github_token`, `clickup_api_token`, `slack_bot_token`, `openai_api_key`) are base64-encoded before persistence.

### 5.2 Environment Variables (Cloud / .env)

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `GITHUB_USERNAME` | GitHub username to track |
| `CLICKUP_API_TOKEN` | ClickUp API v2 token |
| `CLICKUP_TEAM_ID` | ClickUp workspace ID |
| `CLICKUP_USER_ID` | ClickUp user ID |
| `SLACK_BOT_TOKEN` | Slack Bot OAuth token (xoxb-...) |
| `SLACK_CHANNEL` | Channel ID or name for EOD posts |
| `SLACK_USER_ID` | User ID for OOO check & profile |
| `SLACK_DISPLAY_NAME` | Display name on EOD posts |
| `SLACK_ICON_URL` | Profile picture URL |
| `REPORT_HOUR` | Hour (24h) for scheduled report |
| `REPORT_MINUTE` | Minute for scheduled report |
| `TIMEZONE` | IANA timezone (e.g. Asia/Kathmandu) |
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR |
| `APP_ENV` | development, production |

### 5.3 Service Bridge Mapping

`desktop/service_bridge.py` maps config keys to env vars so `app.config.Settings` works without a `.env` file:

```python
_ENV_MAP = {
    "github_token": "GITHUB_TOKEN",
    "github_username": "GITHUB_USERNAME",
    # ... etc
}
```

---

## 6. Scheduler Behavior

### 6.1 Desktop (`LocalScheduler`)

- **Type**: `BackgroundScheduler` (thread-based)
- **Trigger**: `CronTrigger(day_of_week="mon-fri", hour=..., minute=..., timezone=...)`
- **Job**: Calls `app.scheduler.run_eod_pipeline()` in a daemon thread
- **Status events**: `scheduler_started`, `scheduler_stopped`, `pipeline_started`, `pipeline_completed`, `pipeline_error`
- **Next run**: `get_next_run_time()` for UI display

### 6.2 Cloud (`app.scheduler`)

- **Type**: `AsyncIOScheduler` (asyncio)
- **Trigger**: Same cron expression
- **Job**: `_scheduled_eod_job()` → `run_eod_pipeline()`
- **Lifespan**: Started in FastAPI lifespan; stopped on shutdown

---

## 7. Summary Output Format

The summary is built as Slack Block Kit `rich_text` blocks:

1. **Header**: "Updates:"
2. **Development**: Commits and PRs grouped by repo
3. **Task updates**: ClickUp tasks (completed, in-progress, hierarchy)
4. **Additional updates**: Manual bullet points
5. **Next**: In-progress tasks for tomorrow

Plain-text fallback is used for notifications and non–Block Kit clients.

---

## 8. Deployment

### 8.1 Desktop (macOS)

```bash
python3 setup_mac.py py2app
# Output: dist/EOD Reporter.app
```

- **py2app** bundles Python, CustomTkinter, and app code into a standalone `.app`
- Config is stored in `~/Library/Application Support/EOD Reporter/`
- DMG can be built for distribution

### 8.2 Cloud (Docker / Render / Railway / VPS)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- **Endpoints**: `GET /health`, `POST /trigger-eod`
- Scheduler starts on boot; EOD runs Mon–Fri at configured time
- Manual trigger via `POST /trigger-eod` (runs in background task)

---

## 9. Extensibility

| Extension | Approach |
|-----------|----------|
| **AI Summarization** | `ai_summary_service` supports OpenAI-compatible APIs; wire into `DailyActivity.ai_summary` and `summary_service` |
| **Slack discussions in EOD** | Add `slack_activity_service.fetch_slack_channel_activity()` to pipeline; include in `DailyActivity.slack_discussions` |
| **Manual task entry** | Add `POST /tasks` or desktop UI; merge into `manual_updates` |
| **Google Calendar OOO** | Add calendar check before OOO guard in `run_eod_pipeline()` |
| **Multiple channels** | Extend `slack_channel` to support per-team channels |

---

## 10. Dependencies

| Category | Packages |
|----------|----------|
| **Core** | fastapi, uvicorn, pydantic, pydantic-settings |
| **HTTP** | requests |
| **Slack** | slack-sdk |
| **AI** | openai (OpenAI-compatible client) |
| **Scheduler** | APScheduler |
| **Desktop** | customtkinter, py2app |
| **Testing** | pytest, httpx |

---

## 11. File Tree

```
eod-auto-reporter/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Pydantic Settings
│   ├── logger.py
│   ├── scheduler.py         # EOD pipeline + AsyncIOScheduler
│   ├── models/
│   │   ├── __init__.py
│   │   └── activity_models.py
│   └── services/
│       ├── __init__.py
│       ├── github_service.py
│       ├── clickup_service.py
│       ├── slack_service.py
│       ├── slack_activity_service.py
│       ├── ai_summary_service.py
│       └── summary_service.py
├── desktop/
│   ├── main.py              # Desktop entry point
│   ├── app_window.py
│   ├── config_store.py
│   ├── service_bridge.py
│   ├── local_scheduler.py
│   ├── utils.py
│   └── views/
│       ├── dashboard_view.py
│       ├── activity_view.py
│       ├── settings_view.py
│       └── support_view.py
├── docs/
│   └── ARCHITECTURE.md
├── tests/
├── setup_mac.py             # py2app
├── requirements.txt
├── .env.example
└── README.md
```
