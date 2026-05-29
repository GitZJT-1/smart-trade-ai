# Smart Trade AI

[![Test](https://github.com/chefroger/smart-trade-ai/actions/workflows/test.yml/badge.svg)](https://github.com/chefroger/smart-trade-ai/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

[中文](README.md) | [English](README.en.md)

<div align="center">
  <h3>AI Assistant for International Trade Professionals</h3>
  <p>Runs locally · 15 built-in skills · Your data never leaves your machine</p>
</div>

**Your team spends 3 hours a day writing cold emails, researching clients, and managing B2B platforms? This tool compresses that drudgery into 10 minutes.**

So you can focus on what actually matters — closing deals.

---

<p align="center">
  <img src="docs/screenshot-2.png" alt="Customer & Cron Panel" width="75%">
  <br>
  <em>Customer management + Cron task panel</em>
</p>

---

## Why do traders need this?

| Pain Point | Without This Tool | With Smart Trade AI |
|------|-------------|---------|
| Morning Brief | Open 5 websites every morning for FX rates / commodity prices / market news | Auto-generated — live rates, commodity prices, market news + client follow-up reminders |
| Due Diligence | Manual Google → LinkedIn → WHOIS | One-click 6-layer verification: email registration check → WHOIS → sanctions screening → MX verification → tech stack → LinkedIn |
| Cold Emails | Write each one from scratch, forget details when clients pile up | Auto-generated from client profiles, with specific pain-point references |
| B2B Platforms | Manually log in to check Alibaba / Made-in-China every day | Scheduled auto-checks — new inquiries and pending quotes at a glance |
| LinkedIn | Don't know what to post | AI generates weekly content calendar, rotating between industry insights / product cases / engagement polls |
| Client Data | Scattered across Excel / WhatsApp / email | Centralized management, A/B/C grading, linked to document libraries |

---

<p align="center">
  <img src="docs/screenshot-1.png" alt="AI Chat Interface" width="75%">
  <br>
  <em>AI Chat — auto-invokes web_search / read_file / database tools</em>
</p>

---

## Prerequisite: LLM API Key

> **Smart Trade AI is free, but you need your own LLM subscription.** Hermes Agent won't pay for your usage — you must register with a model provider and get an API Key.

Recommended pay-per-token plans (best value for trade workflows):

| Plan | Model | Best For | Price | Sign Up |
|------|-------|----------|-------|---------|
| **Recommended** | DeepSeek V4 Flash | Daily chat, doc analysis, cold emails | ¥1/million tokens | [platform.deepseek.com](https://platform.deepseek.com) → Top-up → API Keys |
| **Alternative** | MiniMax M2.7 | Long-form content, multi-turn conversations | ¥1/million tokens | [minimaxi.cn](https://minimaxi.cn) → Console → Token Plan subscription |

> Avoid pay-as-you-go OpenAI/Anthropic — trade workflows burn a lot of tokens, and per-request billing gets expensive fast.

After getting your API Key, run `hermes setup` in terminal, choose your provider, and paste the key.

---

## Get started in 3 minutes

### Option 1: One-liner install

```bash
curl -fsSL https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh | bash
```

The script handles: Python check → Hermes Agent → Smart Trade AI → 15 skills → database init.

> **Prefer to review before running?**
> ```bash
> curl -fsSLO https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh
> less install.sh       # review, then
> bash install.sh
> ```

### Option 2: Install from Release (pinned version)

Visit [Releases](https://github.com/chefroger/smart-trade-ai/releases) or specify a version:

```bash
git clone --branch v0.4.4 https://github.com/chefroger/smart-trade-ai.git ~/.trade/smart-trade-ai
cd ~/.trade/smart-trade-ai && pip install -e ".[docs]"
install-trade-skills
python server.py
```

### Option 3: Manual install

**Prerequisites**: Python >= 3.11 · Git · LLM API Key (OpenAI / Anthropic / DeepSeek / MiniMax etc.)

```bash
# 1. Install Hermes Agent (AI engine)
git clone --branch main https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent && pip install -e "."

# 2. Configure LLM
hermes setup      # Choose provider, paste API key

# 3. Install Smart Trade AI
git clone --branch main https://github.com/chefroger/smart-trade-ai.git ~/.trade/smart-trade-ai
cd ~/.trade/smart-trade-ai && pip install -e ".[docs]"

# 4. Install skills and launch
install-trade-skills
python server.py
# → Open http://127.0.0.1:9119/trade
```

### Windows

**Before installing, manually install the following:**

| Software | Version | Download | Notes |
|----------|---------|----------|-------|
| **Python** | 3.11 ~ 3.13 | [python.org](https://www.python.org/downloads/) | Download **Windows installer (64-bit)**. Check "Add Python to PATH" during install. |
| **Node.js** | >= 18 LTS | [nodejs.org](https://nodejs.org/) | Download LTS version, default install options are fine (required by some Hermes features). |
| **Git** | Any | [git-scm.com](https://git-scm.com/download/win) | Download **Standalone Installer**, default options are fine. |

> All three have standard Windows GUI installers — double-click → Next → Done, no manual configuration needed.

After installation, **open a new terminal** (PowerShell or CMD) and run:

```powershell
# Verify installations
python --version   # should output Python 3.11.x ~ 3.13.x
node --version     # should output v18.x.x or higher
git --version      # should output git version 2.x.x

# Install Trade
git clone --branch main https://github.com/NousResearch/hermes-agent.git $env:LOCALAPPDATA\hermes\hermes-agent
cd $env:LOCALAPPDATA\hermes\hermes-agent; pip install -e "."; hermes setup

git clone --branch main https://github.com/chefroger/smart-trade-ai.git $env:LOCALAPPDATA\trade\foreign-trade-assistant
cd $env:LOCALAPPDATA\trade\foreign-trade-assistant; pip install -e "."; install-trade-skills

python server.py
```

### Build standalone app (double-click to run, no terminal needed)

```bash
pip install pyinstaller
./scripts/build.sh          # macOS → dist/Smart Trade AI.app
powershell -File scripts/build.ps1  # Windows → dist/Smart Trade AI.exe
```

---

## 15 Professional Skills

### Lead Generation
| Skill | Description |
|------|------|
| Platform Diagnostics | Analyze Alibaba / Made-in-China product pages, output optimization suggestions |
| Social Media Marketing | Generate Facebook / Instagram / TikTok / YouTube content calendars |
| LinkedIn Operations | Profile optimization + content strategy + InMail templates |
| Customs Data | Analyze import/export data, identify high-value buyers |
| Client Development | Generate cold emails and follow-up sequences by target market + product |

### Sales Conversion
| Skill | Description |
|------|------|
| Client Management | A/B/C grading, detail panel, document library linking |
| Document Analysis | Read local PDF / Word / Excel / PPT files, AI auto-parses |
| Business Doc Generation | One-click quotes, proforma invoices, contracts (DOCX / XLSX / PPTX) |
| Quote & Negotiation | Negotiation strategy based on product knowledge base + client profile |

### Productivity Tools
| Skill | Description |
|------|------|
| Due Diligence | 6-layer verification: email → WHOIS → sanctions → MX → tech stack → LinkedIn |
| Morning Brief | Live FX rates + commodities + market news + client follow-up reminders |
| Cron Tasks | Workday automations: morning brief / outreach / social posts / daily summary |
| Chat History | Per-company chat memory, searchable and retraceable |

### System
| Skill | Description |
|------|------|
| Skill Generator | Describe what you need in plain language, auto-generates a new skill + registers it |

---

## Data Security

- **Business data is stored locally by default** (`~/.trade/`), nothing uploaded to any server
- With **Ollama or other local models**, full local operation is possible — no data leaves your machine
- With **OpenAI / Anthropic / DeepSeek / MiniMax or other cloud LLMs**, your input and necessary context are sent to the chosen provider — client identity data is NOT included
- Multi-company isolation (`X-Company-ID` header)
- Bound to `127.0.0.1` — only accessible from your local browser
- **Auto-backup before upgrades** → `~/.trade/backups/`

> **Disclaimer**: Alibaba, LinkedIn, Facebook, Instagram, TikTok, YouTube, WhatsApp and other platform names mentioned in this documentation are trademarks of their respective owners. This tool provides analysis assistance for these platforms and is not affiliated with them. Sanctions data is sourced from OFAC/UN/EU public datasets — results are for reference only and do not constitute legal advice. See [SECURITY.md](SECURITY.md) for details.

---

## Tech Stack

- **AI Engine**: [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT licensed)
- **Backend**: FastAPI + SQLite + uvicorn
- **Frontend**: Vanilla JavaScript SPA (single file, zero build dependencies)
- **LLM**: Compatible with OpenAI / Anthropic / DeepSeek / MiniMax / Ollama etc.
- **Document Parsing**: PyMuPDF / python-docx / openpyxl / python-pptx

---

## Project Structure

```
trade/                     B2B business layer
├── api/                   FastAPI routes (10 business domains)
├── osint/                 Client due diligence module (6-layer verification)
├── skill_router.py        Skill auto-matching engine
├── skill_registry.py      15 skill registry (pure data)
└── ... + 13 business modules

skills/                    15 B2B skills (Markdown-driven)
tests/                     Test coverage (database / business / API / OSINT / smoke)
server.py                  FastAPI entry point
```

---

## Development

```bash
pip install -e ".[dev,docs]"
python -m pytest tests/ -v   # Run tests
ruff check trade/ server.py  # Lint
```

## Documentation

- [Product Requirements (en)](项目需求文档.en.md)
- [Business Overview (en)](业务概览.en.md)
- [Trade Knowledge Base (en)](外贸业务知识库.en.md)
- [Trade Methodology (en)](外贸业务方法总结.en.md)
- [Data Directory Structure (en)](Trade数据目录结构设计.en.md)
- [COMPATIBILITY.md](COMPATIBILITY.md) — Hermes version compatibility
- [Database Schema](docs/database-schema.md)

---

## Contact

<img src="docs/wechat-contact.jpeg" alt="WeChat Contact" width="200">

Scan to add on WeChat (note: "Trade"). For business or support, email lauroge@gmail.com.

---

**Smart Trade AI** — Let AI handle the grind. You handle the deals.
