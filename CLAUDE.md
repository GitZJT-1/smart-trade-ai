# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavior Guidelines

These govern how Claude Code communicates and operates in this repo.

### Communication Style
- **Be concise.** Get to the point. Don't narrate what you're doing — just do it. When explaining a bug root cause, lead with the answer, then provide supporting analysis.
- **Prose over bullets.** Default to natural paragraphs. Use bullet points only when the content is multifaceted enough that prose would be confusing, or when the user asks for a list.
- **Avoid over-formatting.** Don't turn every response into structured sections with bold headers. A heading here and there is fine; a numbered outline on every reply is noise.
- **Match the user's energy.** If they're terse, be terse. If they're detailed, be detailed.
- **Favor showing over summarizing.** When you find a bug, show the relevant code at its file:line. When you fix something, the diff is the explanation.

### When Things Go Wrong
- **Own mistakes directly.** Wrong assumption → say so and correct it. Don't deflect to tool limitations or external factors.
- **Fix and move on.** No long apologies. The user needs the correct result, not contrition.
- **Investigate before asking.** If a tool call fails, diagnose the specific error before raising it. Don't escalate prematurely.

### Code Changes
- **Minimum viable diff.** Fix what was asked for. Don't refactor nearby code, add type hints, or clean up imports unless it's part of the task.
- **Read before edit.** Never change a file you haven't read. The `Edit` tool requires a prior `Read` — that's by design.
- **Trust existing patterns.** New code should look like the code around it. Don't introduce new patterns or abstractions without a reason.
- **Present tradeoffs for non-trivial decisions.** If asked to implement something controversial or architecturally significant, note the alternatives and why you chose one path.

## Git Commit Policy

- 所有 git commit 只使用 `Roger Lau <chefrogerlau@126.com>` 作为作者
- **禁止**在 commit message 中附加 `Co-Authored-By` 行
- **禁止**使用 `git commit --amend` 修改已发布的提交

## Project Overview

Foreign Trade Assistant — a B2B Q&A application for trade/manufacturing sales teams. A FastAPI server wrapping **Hermes Agent** (AI engine from `NousResearch/hermes-agent`) with a custom business layer (multi-company document libraries, customers, chat memory, skill routing) and a single-page chat UI. Also ships as a desktop app (tradewin) via PyWebView.

## Commands

```bash
# Start server (also auto-starts Hermes Gateway for cron scheduling)
python server.py                    # default http://127.0.0.1:9119/trade
python server.py --port 8080 --host 0.0.0.0  # custom port & bind
python server.py --no-browser       # don't open browser on startup
python server.py --no-gateway       # skip auto-launching Hermes Gateway

# Install (editable) + install B2B skills into Hermes
pip install -e ".[dev]"
install-trade-skills                # copy 20 skills from package to ~/.hermes/skills/

# CLI entry points (from pyproject.toml console scripts)
trade                               # shortcut for python server.py
trade-skills-update                 # fetch latest SKILL.md from GitHub main branch
trade-update                        # git pull + pip install + skills + db
trade-backup                        # backup ~/.trade/ data to tar.gz
trade-restore <file.tar.gz>         # restore from backup
tradewin                            # desktop app (FastAPI + pywebview window)

# License management
python -m trade.license generate <申请码> <到期日期>   # 作者生成激活码
python -m trade.license status                          # 查看当前许可证状态

# Pre-install compatibility check
python pre_install_check.py

# Initialize/check database (creates tables + spare columns if missing)
python -m trade.database
```

`HERMES_YOLO_MODE=true` is set programmatically by `trade/bootstrap.py` — no manual env setup needed. Without YOLO mode, the AI agent would prompt for human approval on every tool call.

### Desktop App (tradewin)

```bash
# Install desktop dependencies
pip install -e ".[desktop]"

# Run desktop app (FastAPI backend thread + pywebview window, no external browser needed)
tradewin                              # via console_script
python tradewin.py                    # direct invocation

# Package as standalone .exe
pyinstaller tradewin.spec             # (if spec file exists)
```

`tradewin.py` launches the full Trade server in a daemon thread, waits for it to be ready, then opens a native WebView window pointed at the chat UI. Supports Windows and macOS. `trade/bootstrap.py` and `trade/app.py` include PyInstaller `_MEIPASS` path resolution for bundled static assets.

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
python -m pytest tests/test_license.py -v

# Run a single test
python -m pytest tests/test_business.py::test_function_name -v

# Lint (rules: E/F/W/I/B/C4/UP/N in pyproject.toml; E501/E402/B904/N806/E741/F601 ignored)
ruff check .
ruff check --fix .                 # auto-fix

# Test coverage
coverage run -m pytest tests/ -v
coverage report
```

Tests use temporary databases (monkeypatch `_get_db_path`), no production data is touched. `tests/conftest.py` sets `TRADE_HOME` to a temp directory before any imports to prevent touching real data. `asyncio_mode=auto` handles async test functions automatically. Test files: test_database, test_business, test_api, test_osint, test_chat_smoke, test_license, test_upgrade.

## Pre-install Check

`pre_install_check.py` verifies Hermes Agent is installed and compatible **before** pip installing Trade. It checks:
- Whether `hermes-agent` is installed at all
- Whether the installed version is from the official `NousResearch/hermes-agent` (not the deprecated `chefroger` fork)
- Whether the version meets the minimum requirement (`>= 0.13.0`)
- Queries GitHub API for latest official release

Exit codes: `0` = compatible, `1` = not installed, `2` = incompatible version.

## CI/CD (GitHub Actions)

Three workflows defined in `.github/workflows/`:

1. **test.yml** — Runs on push/PR to `main`. Two-stage pipeline: lint first (ruff + `compileall`), then test across 3 OS (ubuntu/macos/windows) × 3 Python versions (3.11/3.12/3.13). Hermes Agent is NOT installed in CI — tests use mocks/stubs that don't require the full AI engine.

2. **release.yml** — Triggered by `v*` tags or `workflow_dispatch`. Builds macOS `.app` via PyInstaller (`tradewin-mac.spec`), zips it, attaches to GitHub Release. Windows standalone has a separate build flow (see below).

3. **pages.yml** — Triggered by pushes to `docs/` on `main`. Uses Jekyll to build GitHub Pages from `docs/` directory.

## Desktop Builds (PyInstaller)

Four PyInstaller spec files for packaging desktop apps:

| Spec File | Platform | Output |
|-----------|----------|--------|
| `pyinstaller.spec` | Generic/legacy | Single executable |
| `tradewin-mac.spec` | macOS | `TradeWin.app` → `.zip` for release |
| `tradewin-linux.spec` | Linux | Linux executable |
| `windows-standalone/tradewin.spec` | Windows | `TradeWin.exe` via `build.bat` |

```bash
# macOS .app (release pipeline equivalent)
pyinstaller --clean --noconfirm tradewin-mac.spec

# Windows standalone (requires Windows + PySide6)
cd windows-standalone
build.bat     # pip install -r requirements.txt → pip install -e .. → pyinstaller
```

## Architecture

```
windows-standalone/tradewin/    Windows Qt 桌面端 (PySide6) — 独立 exe 构建
  ├── app.py                    MainWindow: QSplitter(侧边栏QTreeWidget + QStackedWidget)
  ├── api.py                    urllib HTTP 客户端（无 httpx/requests，减小打包体积）
  ├── chat.py                   ChatView: SSE 流式渲染 + QTextCursor 增量更新
  ├── views.py                  CustomerView / LibraryView / TasksView / HistoryView / SettingsView
  ├── dialogs.py                对话框（公司/客户/订单/许可证/升级）
  ├── wizard.py                 首次运行配置向导（LLM provider + API Key）
  ├── themes.py                 主题色定义
  ├── tray.py                   系统托盘
  ├── setup.py                  启动引导（session 初始化 + 服务器检测）
  └── resources/
      ├── style.qss             全局 Qt 样式表
      └── icon.ico              应用图标

static/trade_chat.html          Chat SPA — single-file vanilla JS (~2900 lines), served at /trade
        │                         Zero build tools. Injects __TRADE_SESSION_TOKEN__ placeholder.
        ▼
server.py                       Thin entry point (5 lines) — calls bootstrap.setup() + app.main()
tradewin.py                     Desktop app — same backend in daemon thread + pywebview window
  ├── trade/bootstrap.py        Startup sequence: log filter, sys.path, subcommand dispatch,
  │                             Hermes version check, .env load, YOLO mode, skills sync
  ├── trade/app.py              FastAPI app factory + CORS + license check + system endpoints
  │   ├── /trade                Injects session token into SPA HTML
  │   ├── /api/trade/*          Mounts trade.api router (session-token protected)
  │   └── /api/status           Health check
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
        ├─ trade/skill_registry.py 20 skill definitions (pure data — triggers, aliases, formats)
        └─ trade/post_install.py Skill installation + CLI commands (update/backup)
```

## Server Startup Sequence

`trade/bootstrap.py` + `trade/app.py` run a specific, order-dependent startup sequence:

1. **Log noise filter** — suppresses Hermes optional-tool-missing warnings
2. **sys.path bootstrap** — ensures Trade's `trade/` package takes priority over Hermes's `trade/` package; resolves `HERMES_HOME` from env → `~/.hermes/hermes-agent` → `../trade_ai_assistant`
3. **Subcommand dispatch** — `trade update/backup/skills-update` exit early, no server
4. **Architecture check** - `check_native_architecture()` detects Rosetta (x86_64 Python on arm64 Mac); exits with error if mismatch, since Hermes C extensions (pydantic-core, psutil) would fail to load with Mach-O errors
5. **Hermes version check** — `0.13.0 <= version < 0.19.0` (see COMPATIBILITY.md)
6. **Skills sync** — fetches latest SKILL.md from GitHub main; falls back to local hash comparison if offline
7. **Database init** — creates tables, migrates schema, spare columns
8. **License check** — validates license, warns if expired
9. **Session token generation** — random url-safe token injected into HTML and validated by deps.py
10. **Route mounting** — license endpoints → system endpoints (update/backup/restart, no session token required) → trade router
11. **Gateway auto-launch** — spawns `hermes gateway run` as detached subprocess for cron scheduling (unless `--no-gateway`)
12. **PID file** — writes `~/.trade/data/trade.pid`, cleaned up on exit for restart support
13. **Start uvicorn** — binds to `127.0.0.1:9119` by default

## Key Design Decisions

1. **Hermes Agent is an external dependency** (not vendored). Version pinned to `v2026.7.1` in `pyproject.toml`. Compatibility matrix in `COMPATIBILITY.md`.

2. **Session token pattern**: Server generates a random `X-Hermes-Session-Token` on startup, injects it into served HTML. The SPA uses this for API auth — same pattern as Hermes dashboard. `trade/api/deps.py:require_session()` validates it on every protected route.

3. **Single-file SPA frontend**: `static/trade_chat.html` is a ~2900 line vanilla JS application with embedded CSS — no build tools, no framework. Communicates via `__TRADE_SESSION_TOKEN__` placeholder injection. Uses marked.js + DOMPurify for markdown rendering.

4. **Dual chat endpoints**: `/chat` is synchronous (thread pool + 600s timeout); `/chat/stream` uses SSE to emit `tool_start`, `tool_complete`, `thinking`, `response`, `error`, `done` events for real-time tool progress in the UI.

5. **Multi-company isolation via `X-Company-ID` header + session binding**. Every business-data endpoint requires `X-Company-ID`. On first request, the session token is bound to that company — subsequent requests with a different company ID return 403. Use `POST /api/trade/companies/{id}/switch` to explicitly switch. `list_all()` returns only id/name/slug/is_active (PII redacted) for the company selector.

6. **Document libraries = filesystem directories**. Each library has a `root_path` pointing to a real directory. The AI agent uses `read_file` / `list_dir` tools to analyze files.

7. **Skill auto-routing**: `trade/skill_router.py` intercepts every query via `build_query()` and uses keyword/regex matching against 19 skill trigger lists. When matched, it injects a `[SKILL AUGMENTATION]` block with the skill's injection_prompt (loaded from SKILL.md frontmatter, with mtime caching). No match → pass-through with zero added latency.

   The 19 skills are: `b2b-platform`, `b2b-lead-generation`, `b2b-customer-mgmt`, `b2b-document`, `b2b-doc-generation`, `b2b-osint`, `b2b-data-directory`, `b2b-email-intel`, `b2b-social-media`, `b2b-linkedin-marketing`, `b2b-onboarding`, `b2b-customs-data`, `b2b-daily-automation`, `chat-memory`, `b2b-skill-generator`, `b2b-trade-ops`, `b2b-trade-compliance`, `auto-trade-customer-development`, `auto-smtp-email`.

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

18. **License system**: Ed25519 non-asymmetric signatures — public key built into code, private key held by author only. Activation codes embed machine-id hash + expiry date + Ed25519 signature. 30-day free trial, machine-bound activation (soft-delete on company removal, audit logs at `~/.trade/audit/`).

19. **Desktop app (tradewin.py)**: PyWebView native window wrapping the same FastAPI backend in a daemon thread. No external browser needed. `[desktop]` optional dependency group includes `pywebview` + `pyinstaller`. Bootstrap and app modules support PyInstaller `_MEIPASS` for bundled static files.

20. **Token cost optimization** (2026-06-12): Two mechanisms to reduce repeated token spending for MiniMax M3 pay-per-token model:
    - **System prompt tiering**: `build_query()` checks `conversations` table — first message in a company session gets full `TRADE_SYSTEM_PROMPT`, subsequent messages get `TRADE_SYSTEM_PROMPT_MINIMAL` (~400 vs ~2500 tokens). `TRADE_SYSTEM_PROMPT_MINIMAL` only has Disclaimer + Role + Language Policy + Company Isolation.
    - **Skill injection caching**: `chat.py` maintains per-company `_last_skill_per_company` dict. Consecutive use of the same skill sends a brief hint (`"继续使用 {name} 技能，规则同上一次。"`) instead of the full injection_prompt (~1500 tokens). Process restart clears cache (safe degradation).
    - Rollback tag: `pre-token-optimization` points to the commit before these changes.

21. **Upgrade pipeline** (`trade/post_install.py`): `update_trade()` operates exclusively in `~/.trade/foreign-trade-assistant/` (the runtime directory) — no source-directory guessing or sync. `_perform_restart()` starts the new process first, then kills the old one (avoids the old "suicide before spawn" deadlock). The new process retries `uvicorn.run` for up to 10 seconds waiting for the old process to release the port. Windows uses `creationflags=0x00000200` (CREATE_NEW_PROCESS_GROUP) for clean subprocess detachment. `_latest_version_cache` (TTL 600s) prevents GitHub API rate-limiting on repeated version checks. `_capture_output` catches `SystemExit` so `sys.exit()` no longer causes FastAPI 500 errors. Failure markers cover `pip install failed`, `git stash failed`, and `Database check failed`.

22. **Mac M-chip architecture detection** (2026-07-13): 6 defense lines prevent Rosetta Python from installing x86_64 C extensions (pydantic-core, psutil) that cause Hermes Mach-O load failures and Trade 422 errors. (1) `install.sh` searches `/opt/homebrew/bin/python3.*` for native arm64 Python, exits if not found. (2) `pre_install_check.py` returns exit code 3 on arch mismatch. (3) `bootstrap.py:check_native_architecture()` blocks startup with `sys.exit(1)`. (4) `post_install/update.py` Step 0 blocks upgrade with `architecture_mismatch` error. (5) `app.py:_perform_restart()` switches to native Python on Rosetta. (6) `app.py:_ensure_gateway_running()` uses `/opt/homebrew/bin/hermes` on Rosetta.

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

## Docs & GitHub Pages

`docs/` 目录的 markdown 文档通过 GitHub Actions (`pages.yml`) 自动部署到 GitHub Pages。Jekyll 构建，源文件推送到 `main` 分支的 `docs/` 目录即自动触发部署。

## Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `scripts/install.sh` | macOS/Linux | 一键安装（Hermes + Trade + skills + DB） |
| `scripts/install.ps1` | Windows | 一键安装 PowerShell 版 |
| `scripts/install_prereqs.sh` | macOS/Linux | 前置条件检查 |
| `scripts/install_prereqs.ps1` | Windows | 前置条件检查 PowerShell 版 |
| `scripts/build.sh` | macOS/Linux | 开发构建 |
| `scripts/build.ps1` | Windows | 开发构建 PowerShell 版 |
| `scripts/com.foreign-trade.gateway.plist` | macOS | LaunchAgent plist（Hermes Gateway 开机自启） |

## Multi-Platform Sync

代码修改需同步三平台（跨平台一致性规则）：
1. **Web 前端** (`static/trade_chat.html`) — 所有 UI 功能的核心实现
2. **Windows Qt 桌面端** (`windows-standalone/tradewin/`) — views.py / dialogs.py / chat.py / api.py
3. **macOS desktop** (`tradewin.py`) — PyWebView 封装

修改涉及 API 时需同步更新：api/views/spec/dialogs 四层。

## Skills Sync Mechanism

Skills live in two places:
1. **Source of truth**: `skills/b2b-*/SKILL.md` in the project directory (version controlled)
2. **Runtime**: `~/.hermes/skills/b2b-*/SKILL.md` (what Hermes actually loads)

Sync happens at three points:
- `trade/bootstrap.py` startup — fetches latest from GitHub main, falls back to local hash comparison
- `trade-skills-update` CLI — same GitHub fetch logic
- UI "更新 Skills" button — calls `POST /api/trade/skills/update` (same update logic)

`trade/skill_registry.py` is the **pure-data registry** of all 20 skills (triggers, aliases, input/output formats). Adding a new skill requires: (1) create `skills/b2b-{name}/SKILL.md` 或 `skills/auto-{name}/SKILL.md`, (2) add an entry to `_SKILLS` in `skill_registry.py`.

## Runtime Data Layout

详见 [Trade数据目录结构设计.md](Trade数据目录结构设计.md)。

```
~/.hermes/skills/               Skills installed by install-trade-skills
  ├── b2b-document/
  ├── b2b-platform/
  └── ... (17 b2b-* skills)
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

The SPA uses vanilla JS with a custom view-caching router (~2900 lines of vanilla JS + embedded CSS):
- **`navToView(view, chatCtx, chatName)`** — switches between chat/customers/tasks/history views. Creates DOM once, caches in `viewCache` object, hides/shows on switch. Non-cached children (except `#guidance-bar`) are removed on each switch.
- **`api(method, path, body)`** — central fetch wrapper. Adds `X-Hermes-Session-Token` + `X-Company-ID` headers. 120s AbortController timeout. Handles 401/402/404/409 with toast. Returns parsed JSON or null.
- **`$ (id)`** — shorthand for `document.getElementById(id)`.
- **Guidance bar** — `#guidance-bar` is a fixed-height banner (flex-shrink:0, max-height:20vh, scrollable) at the top of `#main-content`. Shows current task guidance + progress bar + today's cron task list. Preserved across view switches (skipped in cleanup loop).
- **Modals** — a mix of static hidden divs (company-modal, customer-modal, library-modal) toggled via `showModal(id)`/`hideModal(id)`, and dynamically-created backdrops (order-modal, customer-detail-panel, custom-template-modal) that must clean up old instances before creating new ones to avoid duplicate IDs.
- **Chat** — SSE streaming via `EventSource`-like fetch reader. Tool progress events (`tool_start`, `tool_complete`, `thinking`, `response`, `error`, `done`) rendered inline. Markdown via marked.js + DOMPurify.

## Chat Memory

Every chat message (query + response) is persisted to SQLite `conversations` table with `created_at` auto-populated via `datetime('now', 'localtime')` default. Both `/chat` and `/chat/stream` call `chat_memory.save_with_context()` after agent response, which also optionally syncs to Hindsight long-term memory and Hermes native memory.

## GBrain Configuration (configured by /setup-gbrain)
- Mode: local-stdio
- Engine: pglite
- Config file: ~/.gbrain/config.json (mode 0600)
- Setup date: 2026-06-10
- MCP registered: yes
- Artifacts sync: artifacts-only
- Current repo policy: read-write

## Code Annotation Standards

Every function must have a Chinese docstring. Every if-branch must have a comment explaining the business logic. Complex list/dict comprehensions should be split with inline comments. Sections separated by banner comments (`# ====`).
