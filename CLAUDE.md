# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Foreign Trade Assistant — a B2B Q&A application for trade/manufacturing sales teams. A FastAPI server wrapping **Hermes Agent** (AI engine from `NousResearch/hermes-agent`) with a custom business layer (multi-company document libraries, customers, chat memory, skill routing) and a single-page chat UI.

## Commands

```bash
# Start server (also auto-starts Hermes Gateway for cron scheduling)
python server.py                    # default http://127.0.0.1:9119/trade
python server.py --port 8080 --host 0.0.0.0  # custom port & bind
python server.py --no-browser       # don't open browser on startup
python server.py --no-gateway       # skip auto-launching Hermes Gateway

# Install (editable) + install B2B skills into Hermes
pip install -e ".[dev]"
install-trade-skills                # copy 15 skills from package to ~/.hermes/skills/

# CLI entry points (from pyproject.toml console scripts)
trade                               # shortcut for python server.py
trade-skills-update                 # fetch latest SKILL.md from GitHub main branch
trade-update                        # git pull + pip install + skills + db
trade-backup                        # backup ~/.trade/ data to tar.gz

# Pre-install compatibility check
python pre_install_check.py

# Initialize/check database (creates tables + spare columns if missing)
python -m trade.database
```

The server requires `HERMES_YOLO_MODE=true` in the environment (set by Hermes .env, or export manually). Without it, the AI agent will prompt for human approval on every tool call — unworkable for this product's target users (SECURITY.md).

## Testing & Linting

```bash
# Run all tests (asyncio_mode=auto, configured in pyproject.toml [tool.pytest.ini_options])
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_business.py -v
python -m pytest tests/test_api.py -v
python -m pytest tests/test_database.py -v
python -m pytest tests/test_chat_smoke.py -v
python -m pytest tests/test_osint.py -v

# Run a single test
python -m pytest tests/test_business.py::test_function_name -v

# Lint (rules configured in pyproject.toml [tool.ruff])
ruff check .
ruff check --fix .                 # auto-fix

# Test coverage
coverage run -m pytest tests/ -v
coverage report
```

Tests use temporary databases (monkeypatch `_get_db_path`), no production data is touched. `tests/conftest.py` sets `TRADE_HOME` to a temp directory before any imports to prevent touching real data. `asyncio_mode=auto` handles async test functions automatically. 127 tests across 5 files (test_database, test_business, test_api, test_osint, test_chat_smoke).

## Architecture

```
static/trade_chat.html          Chat SPA — single-file vanilla JS (~2600 lines), served at /trade
        │                         Zero build tools. Injects __TRADE_SESSION_TOKEN__ placeholder.
        ▼
server.py                       FastAPI entry point — complex startup sequence (see below)
  ├── /trade                    Injects session token into SPA HTML
  ├── /api/trade/*              Mounts trade.api router (session-token protected)
  ├── /api/status               Health check
        │
        ▼
trade/api/__init__.py           FastAPI router aggregator — all B2B endpoints
  │                             All sub-routers share Depends(require_session)
  ├── trade/api/companies.py     /companies/*     Multi-company CRUD
  ├── trade/api/libraries.py     /libraries/*     Document library CRUD + file upload
  ├── trade/api/customers.py     /customers/*     Customer CRUD + library linking
  ├── trade/api/orders.py        /orders/*        Order CRUD (3-layer context query)
  ├── trade/api/conversations.py /conversations/* Chat log CRUD
  ├── trade/api/chat.py          /chat (sync) + /chat/stream (SSE with tool progress)
  ├── trade/api/memory.py        /memory/*        Hindsight long-term memory + LLM providers
  ├── trade/api/onboarding.py    /onboarding/*    First-run wizard
  ├── trade/api/cron.py          /cron/*          Scheduled task automation
  ├── trade/api/deps.py          Session token validation + _require_company()
  ├── trade/api/models.py        Pydantic request/response models
  └── trade/api/license.py       License validation endpoints
        │
        ├─ trade/helpers.py     Provider check, agent kwargs, query builder
        │     ├─ trade/prompts.py     System prompt loader (file → DB → code fallback)
        │     │     └─ trade/prompt.py   TRADE_SYSTEM_PROMPT (B2B agent personality)
        │     └─ trade/skill_router.py  Keyword-based skill auto-detection + query augmentation
        │
        ├─ trade/database.py    SQLite connection + schema (data/trade.db)
        │     ├─ trade/company.py       Multi-company CRUD + ~/.trade/ data dir management
        │     ├─ trade/library.py       Document library CRUD
        │     ├─ trade/customer.py      Customer CRUD + library associations
        │     ├─ trade/order.py         Order CRUD (3-layer context query)
        │     └─ trade/chat_memory.py   Conversation log + Hindsight bridge
        │           └─ trade/memory.py  Hindsight long-term memory client
        │
        ├─ trade/onboarding.py  First-run wizard (create company + agent identity in one step)
        ├─ trade/osint/         B2B due-diligence (6-layer subpackage)
        │     ├── orchestrator.py  osint_full_check() main entry
        │     ├── whois.py         Layer 2: WHOIS domain lookup
        │     ├── email_verify.py  Layer 3: corporate vs personal email
        │     ├── sanctions.py     Layer 4: OFAC/UN/EU sanctions screening
        │     ├── tech_stack.py    Layer 5: tech stack detection
        │     ├── linkedin_verify.py Layer 6: LinkedIn verification
        │     ├── scoring.py       Risk score + recommendation
        │     └── constants.py     Shared constants
        ├─ trade/email_intel.py Email background check (120+ platform detection via holehe)
        ├─ trade/license.py     License validation
        ├─ trade/skill_registry.py 15 skill definitions (pure data — triggers, aliases, formats)
        └─ trade/post_install.py Skill installation + CLI commands (update/backup)
```

## Server Startup Sequence

`server.py` runs a specific, order-dependent startup sequence:

1. **Log noise filter** — suppresses Hermes optional-tool-missing warnings
2. **sys.path bootstrap** — ensures Trade's `trade/` package takes priority over Hermes's `trade/` package; resolves `HERMES_HOME` from env → `~/.hermes/hermes-agent` → `../trade_ai_assistant`
3. **Subcommand dispatch** — `trade update/backup/skills-update` exit early, no server
4. **Hermes version check** — `0.13.0 <= version < 0.16.0` (see COMPATIBILITY.md)
5. **Skills sync** — fetches latest SKILL.md from GitHub main; falls back to local hash comparison if offline
6. **Database init** — creates tables, migrates schema, spare columns
7. **License check** — validates license, warns if expired
8. **Session token generation** — random url-safe token injected into HTML and validated by deps.py
9. **Route mounting** — license endpoints → system endpoints (update/backup/restart, no session token required) → trade router
10. **Gateway auto-launch** — spawns `hermes gateway run` as detached subprocess for cron scheduling (unless `--no-gateway`)
11. **PID file** — writes `~/.trade/data/trade.pid`, cleaned up on exit for restart support
12. **Start uvicorn** — binds to `127.0.0.1:9119` by default

## Key Design Decisions

1. **Hermes Agent is an external dependency** (not vendored). Version pinned to `v2026.5.28` (0.15.0) in `pyproject.toml`. Compatibility matrix in `COMPATIBILITY.md`.

2. **Session token pattern**: Server generates a random `X-Hermes-Session-Token` on startup, injects it into served HTML. The SPA uses this for API auth — same pattern as Hermes dashboard. `trade/api/deps.py:require_session()` validates it on every protected route.

3. **Single-file SPA frontend**: `static/trade_chat.html` is a ~2600 line vanilla JS application with embedded CSS — no build tools, no framework. Communicates via `__TRADE_SESSION_TOKEN__` placeholder injection. Uses marked.js + DOMPurify for markdown rendering.

4. **Dual chat endpoints**: `/chat` is synchronous (thread pool + 600s timeout); `/chat/stream` uses SSE to emit `tool_start`, `tool_complete`, `thinking`, `response`, `error`, `done` events for real-time tool progress in the UI.

5. **Multi-company isolation via `X-Company-ID` header**. Every business-data endpoint requires this header. `require_company()` validates the company exists and is active; `opt_company()` allows optional company context. Database queries always filter by `company_id`.

6. **Document libraries = filesystem directories**. Each library has a `root_path` pointing to a real directory. The AI agent uses `read_file` / `list_dir` tools to analyze files.

7. **Skill auto-routing**: `trade/skill_router.py` intercepts every query via `build_query()` and uses keyword/regex matching against 15 skill trigger lists. When matched, it injects a `[SKILL AUGMENTATION]` block with the skill's injection_prompt (loaded from SKILL.md frontmatter, with mtime caching). No match → pass-through with zero added latency.

   The 15 skills are: `b2b-platform`, `b2b-lead-generation`, `b2b-customer-mgmt`, `b2b-document`, `b2b-doc-generation`, `b2b-osint`, `b2b-data-directory`, `b2b-email-intel`, `b2b-social-media`, `b2b-linkedin-marketing`, `b2b-onboarding`, `b2b-customs-data`, `b2b-daily-automation`, `chat-memory`, `b2b-skill-generator`.

8. **Prompt resolution chain** (trade/prompts.py): Company identity file (~/.trade/companies/{slug}/agent_identity.md) → DB agent_identity_md field → global system.md → code fallback (TRADE_SYSTEM_PROMPT). Files are mtime-cached for performance.

9. **Hindsight is optional**. `trade/memory.py` gracefully degrades to no-ops if `hindsight_client` is not installed. Also writes to Hermes native memory (~/.hermes/memories/MEMORY.md) which always works.

10. **Spare columns pattern**: All DB tables have `extra1/extra2/extra3` TEXT columns (storing JSON) for future schema extensions without ALTER TABLE. `_add_spare_columns()` is idempotent across all tables.

11. **Onboarding flow**: `POST /api/trade/onboarding/first-company` atomically creates a company + configures agent identity. Protected by an in-memory flag that checks DB for existing active companies.

12. **Hermes Gateway auto-launch**: On startup, `server.py` checks if `hermes gateway run` is already listening on port 8642. If not, it spawns it as a detached subprocess (independent lifecycle — Gateway survives Trade restart). This enables cron scheduling for automated tasks.

13. **Skills sync on startup**: `server.py` fetches latest SKILL.md from GitHub main branch on every startup. Falls back to local hash comparison if offline. Skills are never deleted (user may have added their own).

14. **Data templates**: `.trade-template/` contains structured templates for companies (agent identity, products, competitors, certifications, marketing strategy, sales playbook), clients (profiles, contacts, orders, quotes, requirements), and libraries.

15. **OSINT subpackage**: `trade/osint/` is a 6-layer due-diligence pipeline (email registration → WHOIS → email verification → sanctions → tech stack → LinkedIn verification), coordinated by `orchestrator.py`. All functions are pure (no DB, no filesystem). `trade/email_intel.py` is a separate module using `holehe` CLI under subprocess for 120+ platform email registration checks.

16. **Orders API**: `trade/api/orders.py` + `trade/order.py` provide 3-layer context query (company scope, customer scope, order details). Each order links to a customer, which belongs to a company — ensuring correct data isolation.

17. **Test conftest isolation**: `tests/conftest.py` sets `TRADE_HOME` env var to a temp directory before any imports, ensuring tests never touch real user data.

## Hermes Coupling Points

Trade depends on these Hermes internals (watch on Hermes upgrades):
- `run_agent.AIAgent` — the AI agent class (imported dynamically in chat endpoints)
- `hermes_cli.config.load_config` — reads `~/.hermes/config.yaml`
- `hermes_cli.config.DEFAULT_CONFIG` — v0.14+ `config["model"]` 是扁平字符串 `"provider:model"`，v0.13 前是嵌套 dict `{"provider":"...","default":"..."}`
- `hermes_cli.auth.PROVIDER_REGISTRY` — available LLM providers
- `hermes_cli.env_loader.load_hermes_dotenv` — loads `~/.hermes/.env`
- `hermes_cli.models._PROVIDER_MODELS` — provider-to-models mapping (v0.14 替换 name_to_models)
- `hermes_constants.get_hermes_home` — resolves `~/.hermes` path
- Cognee knowledge graph (tools `cognee_remember` / `cognee_recall` referenced in system prompt)
- `hermes gateway run` — spawned as detached subprocess for cron scheduling (port 8642)

## Skills Sync Mechanism

Skills live in two places:
1. **Source of truth**: `skills/b2b-*/SKILL.md` in the project directory (version controlled)
2. **Runtime**: `~/.hermes/skills/b2b-*/SKILL.md` (what Hermes actually loads)

Sync happens at three points:
- `server.py` startup — fetches latest from GitHub main, falls back to local hash comparison
- `trade-skills-update` CLI — same GitHub fetch logic
- UI "更新 Skills" button — calls `POST /api/trade/skills/update` (same update logic)

`trade/skill_registry.py` is the **pure-data registry** of all 15 skills (triggers, aliases, input/output formats). Adding a new skill requires: (1) create `skills/b2b-{name}/SKILL.md`, (2) add an entry to `_SKILLS` in `skill_registry.py`.

## Runtime Data Layout

详见 [Trade数据目录结构设计.md](Trade数据目录结构设计.md)。

```
~/.hermes/skills/               Skills installed by install-trade-skills
  ├── b2b-document/
  ├── b2b-platform/
  └── ... (15 b2b-* skills)
~/.trade/                       User data created on first company init
  ├── config.yaml
  ├── prompts/system.md
  └── companies/{slug}/
      ├── agent-identity.md
      ├── company-profile.md
      ├── products.md
      └── ...
```

## Frontend Architecture (static/trade_chat.html)

The SPA uses vanilla JS with a custom view-caching router:
- **`navToView(view, chatCtx, chatName)`** — switches between chat/customers/tasks/history views. Creates DOM once, caches in `viewCache` object, hides/shows on switch. Non-cached children (except `#guidance-bar`) are removed on each switch.
- **`api(method, path, body)`** — central fetch wrapper. Adds `X-Hermes-Session-Token` + `X-Company-ID` headers. 120s AbortController timeout. Handles 401/402/404/409 with toast. Returns parsed JSON or null.
- **`$ (id)`** — shorthand for `document.getElementById(id)`.
- **Guidance bar** — `#guidance-bar` is an absolute-positioned banner inserted into `#main-content`. It's preserved across view switches (skipped in cleanup loop). Rendered by `_renderGuidanceBar()` with cron task schedule matching.
- **Modals** — a mix of static hidden divs (company-modal, customer-modal, library-modal) toggled via `showModal(id)`/`hideModal(id)`, and dynamically-created backdrops (order-modal, customer-detail-panel, custom-template-modal) that must clean up old instances before creating new ones to avoid duplicate IDs.
- **Chat** — SSE streaming via `EventSource`-like fetch reader. Tool progress events (`tool_start`, `tool_complete`, `thinking`, `response`, `error`, `done`) rendered inline. Markdown via marked.js + DOMPurify.

## Chat Memory

Every chat message (query + response) is persisted to SQLite `conversations` table with `created_at` auto-populated via `datetime('now', 'localtime')` default. Both `/chat` and `/chat/stream` call `chat_memory.save_with_context()` after agent response, which also optionally syncs to Hindsight long-term memory and Hermes native memory.

## Code Annotation Standards

Every function must have a Chinese docstring. Every if-branch must have a comment explaining the business logic. Complex list/dict comprehensions should be split with inline comments. Sections separated by banner comments (`# ====`).
