# Repository Guidelines

Foreign Trade Assistant — a B2B Q&A application for trade/manufacturing sales teams. A FastAPI server wrapping **Hermes Agent** with multi-company document libraries, customers, chat memory, skill routing, and a single-page chat UI. Also ships as a desktop app (tradewin) via PyWebView.

## Project Structure & Module Organization

```
static/trade_chat.html        Vanilla JS SPA (~3650 lines), served at /trade
server.py / tradewin.py       Entry points (web server / desktop app)
trade/                        Core Python package
  ├── api/                    FastAPI routers (chat, companies, customers, orders,
  │                             cron, conversations, libraries, license, memory,
  │                             onboarding, models, deps)
  ├── company/                Multi-company workdir management (crud.py, workdir.py)
  ├── osint/                  6-layer B2B due-diligence pipeline
  ├── database.py             SQLite schema + connection
  ├── customer.py             Customer CRUD, dedup, completeness scoring, briefing, health audit
  ├── chat_memory.py          Conversation log + rating + lifecycle (365-day / 30k-threshold cleanup)
  ├── skill_registry.py       34 skill definitions (triggers, aliases, augment prompts)
  ├── skill_router.py         Skill matching, frontmatter parsing, query augmentation
  ├── prompt.py               System prompts (full, minimal, OSINT, brand safety)
  ├── prompts.py              Prompt resolution chain (file → DB → code fallback)
  ├── helpers.py              Query builder with skill routing + brand safety injection
  ├── email_intel.py          Email intelligence & lookup
  ├── onboarding.py           New-user onboarding wizard (OSINT + cold outreach)
  ├── memory.py               Agent memory & context management
  ├── bootstrap.py            First-run environment setup
  ├── app.py                  Application lifecycle & startup
  └── license.py              Ed25519 license validation + self-recovery
skills/                       34 skill markdown files (version controlled)
tests/                        9 test files, ~230 tests
```

## Build, Test, and Development Commands

```bash
# Install (editable) + skills
pip install -e ".[dev]"
install-trade-skills

# Start server
python server.py                          # http://127.0.0.1:9119/trade
python server.py --no-gateway             # skip Hermes Gateway auto-launch
tradewin                                  # desktop app (requires pip install -e ".[desktop]")

# CLI tools
trade-skills-update                       # fetch latest SKILL.md from GitHub
trade-update                              # git pull + pip install + skills + db
trade-backup                              # backup ~/.trade/ to tar.gz

# Testing
python -m pytest tests/ -v                # all tests (asyncio_mode=auto)
python -m pytest tests/test_customer_dedup.py -v  # single file

# Lint
ruff check .                              # rules: E/F/W/I/B/C4/UP/N
ruff check --fix .                        # auto-fix

# Coverage
coverage run -m pytest tests/ -v && coverage report
```

## Coding Style & Naming Conventions

- **Python**: Chinese docstrings on every function; every `if`-branch commented with business logic; sections delimited by `# ====` banner comments.
- **Frontend**: Vanilla JS, no build tools. `$ (id)` shorthand, `api(method, path, body)` central fetch wrapper with 120s timeout, view-caching router via `navToView()`.
- **Linting**: Ruff with select `E/F/W/I/B/C4/UP/N`; ignores `E501/E402/B904/N806/E741/F601`.
- **Database**: Spare columns pattern (`extra1/extra2/extra3`) for schema flexibility; all tables use `datetime('now', 'localtime')` for timestamps.

## Testing Guidelines

- Framework: **pytest** with `asyncio_mode=auto`. 8 test files, ~225 tests.
- Isolation: `tests/conftest.py` sets `TRADE_HOME` to a temp directory before imports — no real data touched.
- Database: monkeypatch `_get_db_path` for temporary SQLite databases.
- Key test files: `test_customer_dedup.py` (dedup, completeness, briefing, health), `test_api.py`, `test_osint.py`, `test_chat_smoke.py`, `test_license.py`.
- Run: `python -m pytest tests/ -v`

## Key Design Points

1. **34 skills** with registry + disk files: OSINT, email-intel, lead-generation, document, doc-generation, platform, linkedin-marketing, social-media, customs-data, onboarding, daily-automation, customer-mgmt, data-directory, chat-memory, skill-generator, trade-ops, trade-compliance, cold-outreach, email-imitation, buyer-persona, market-analysis, sales-pipeline, inquiry-training, kol-imitation, reddit-engagement, seo-aeo, short-video, exhibition, product-description, customer-intel, six-thinking-hats, customer-finder, auto-trade-customer-development, ~~auto-smtp-email~~.
2. **Brand Safety Guardrails**: `BRAND_SAFETY_BLOCK` in `trade/prompt.py` prohibits derogatory language, fabricated certifications, hype claims, and competitor attacks. Loaded per-company via `get_brand_safety()` or falls back to code default. Injected into system prompt in `build_query()`.
3. **Customer Dedup & Health**: Soft dedup warnings on `create()`; `bulk_save()` 3-dimensional dedup (name + email + website); `find_duplicates()` email exact match + website domain-normalized match; `compute_data_completeness()` weighted 0–100 score across 16 fields; `build_briefing()` AI customer briefing; `health_audit()` detects stale customers, high-value unconverted, and incomplete data.
4. **Conversation Lifecycle**: Automatic daily cleanup via `purge_old_conversations()` — removes conversations older than 365 days only when total exceeds 30,000 records. Rate-limited to once per day. Per-company scoped.
5. **Conversation Rating**: `POST /conversations/{id}/rate` (1–5 + feedback), stored via `json_set` atomic UPDATE. SSE stream returns `conversation_id` in response event for immediate frontend rating.
6. **Onboarding Wizard**: Two-step guided flow for new users — OSINT company lookup + cold outreach email generation.
7. **Multi-Company Workdirs**: `trade/company/` manages per-company desktop working directories with document library auto-registration.

## Commit & Pull Request Guidelines

- **Commits**: Chinese-language conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `style:`). Keep scoped and atomic.
- **PRs**: Link related issues; include before/after test results; screenshots for UI changes. Ensure `ruff check .` and `python -m pytest tests/ -v` pass.

## Code Annotation Standards

Every function must have a Chinese docstring. Every if-branch must have a comment explaining the business logic. Complex list/dict comprehensions should be split with inline comments. Sections separated by banner comments (`# ====`).
