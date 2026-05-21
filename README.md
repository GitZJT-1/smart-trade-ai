# Smart Trade AI

[![Test](https://github.com/chefroger/smart-trade-ai/actions/workflows/test.yml/badge.svg)](https://github.com/chefroger/smart-trade-ai/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

[中文](README.md) | [English](README.en.md)

<div align="center">
  <h3>外贸业务员的 AI 助手</h3>
  <p>本地运行 · 14 项专业能力 · 数据不出电脑</p>
</div>

**你的外贸团队每天花 3 小时写开发信、查客户背景、维护 B2B 平台？这个工具帮你把重复劳动压缩到 10 分钟。**

让你专注于最重要的那件事——跟客户谈生意。

---

<p align="center">
  <img src="docs/screenshot-2.png" alt="Customer & Cron Panel" width="75%">
  <br>
  <em>客户管理 + 定时任务面板</em>
</p>

---

## 为什么外贸人需要这个？

| 痛点 | 不用这个工具 | 用了之后 |
|------|-------------|---------|
| 早安简报 | 每天打开 5 个网站查汇率/金价/新闻 | 自动生成，含实时汇率+大宗商品行情+客户跟进提醒 |
| 客户背调 | 手动 Google → LinkedIn → WHOIS | 一键 6 层验证：邮箱注册检测→WHOIS→制裁名单→邮箱验证→技术栈→LinkedIn |
| 开发信 | 每封手动写，客户多了记不清 | 根据客户画像自动生成，带具体痛点引用 |
| B2B 平台 | 每天登录阿里国际站/中国制造网看数据 | 定时自动检查，新询盘/待跟进报价一目了然 |
| LinkedIn | 不知道发什么内容 | AI 按周生成内容日历，轮换行业洞察/产品案例/互动提问 |
| 客户资料 | 散落在 Excel/微信/邮件里 | 统一管理，A/B/C 分级，关联文档库 |

---

<p align="center">
  <img src="docs/screenshot-1.png" alt="AI Chat Interface" width="75%">
  <br>
  <em>AI 对话界面 — 自动调用 web_search / read_file / database 工具</em>
</p>

---

## 3 分钟上手

### 方式一：一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh | bash
```

脚本自动完成：Python 环境检查 → Hermes Agent → Trade 安装 → 14 个 skills → 数据库初始化。

> **如果你希望安装前先审查脚本**：
> ```bash
> curl -fsSLO https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh
> less install.sh       # 审查后
> bash install.sh
> ```

### 方式二：从 Release 安装（固定版本）

访问 [Releases](https://github.com/chefroger/smart-trade-ai/releases) 下载最新版，或指定版本：

```bash
git clone --branch v0.4.4 https://github.com/chefroger/smart-trade-ai.git ~/.trade/smart-trade-ai
cd ~/.trade/smart-trade-ai && pip install -e ".[docs]"
install-trade-skills
python server.py
```

### 方式三：手动安装

**前置条件**：Python >= 3.11 · Git · LLM API Key（OpenAI / Anthropic / DeepSeek / MiniMax 等）

```bash
# 1. 安装 Hermes Agent（AI 引擎）
git clone --branch main https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent && pip install -e "."

# 2. 配置 LLM
hermes setup      # 按提示选择 provider、填入 API Key

# 3. 安装 Smart Trade AI
git clone --branch main https://github.com/chefroger/smart-trade-ai.git ~/.trade/foreign-trade-assistant
cd ~/.trade/foreign-trade-assistant && pip install -e ".[docs]"

# 4. 安装 skills 并启动
install-trade-skills
python server.py
# → 浏览器打开 http://127.0.0.1:9119/trade
```

### Windows

```powershell
git clone --branch main https://github.com/NousResearch/hermes-agent.git $env:LOCALAPPDATA\hermes\hermes-agent
cd $env:LOCALAPPDATA\hermes\hermes-agent; pip install -e "."; hermes setup

git clone --branch main https://github.com/chefroger/smart-trade-ai.git $env:LOCALAPPDATA\trade\foreign-trade-assistant
cd $env:LOCALAPPDATA\trade\foreign-trade-assistant; pip install -e "."; install-trade-skills

python server.py
```

### 打包为独立应用（双击运行，无需终端）

```bash
pip install pyinstaller
./scripts/build.sh          # macOS → dist/Smart Trade AI.app
powershell -File scripts/build.ps1  # Windows → dist/Smart Trade AI.exe
```

---

## 14 项专业能力

### 获客引流
| 能力 | 说明 |
|------|------|
| 平台诊断 | 分析阿里国际站/中国制造网产品页面，输出优化建议 |
| 社媒营销 | 生成 Facebook/Instagram/TikTok/YouTube 内容日历 |
| LinkedIn 运营 | Profile 优化 + 内容策略 + InMail 模板 |
| 海关数据 | 分析进出口数据，筛选高价值采购商 |
| 客户开发 | 根据目标市场+产品生成开发信和跟进序列 |

### 销售转化
| 能力 | 说明 |
|------|------|
| 客户管理 | A/B/C 分级、详情面板、文档库关联 |
| 文档分析 | 读取本地 PDF/Word/Excel/PPT，Agent 自动解析 |
| 商务文档生成 | 一键生成报价单、PI、合同（DOCX/XLSX/PPTX） |
| 报价谈判 | 基于产品知识库和客户画像给出谈判策略 |

### 效率工具
| 能力 | 说明 |
|------|------|
| 客户背调 | 6 层验证：邮箱→WHOIS→制裁→邮箱验证→技术栈→LinkedIn |
| 今日简报 | 实时汇率+大宗商品+市场新闻+客户跟进提醒 |
| 定时任务 | 7 个工作日自动化：早安简报/开发信/社媒/晚间总结 |
| 对话记录 | 按公司隔离的聊天记忆，支持搜索/回溯 |

---

## 数据安全

- **业务数据默认存储在本地**（`~/.trade/`），不上传任何服务器
- 如使用 **Ollama 等本地模型**，可实现完整本地运行，数据完全不出电脑
- 如使用 **OpenAI / Anthropic / DeepSeek / MiniMax 等云端 LLM**，用户输入和必要上下文会发送至所选服务商——不包含客户身份信息
- 多公司数据隔离（`X-Company-ID` header）
- 绑定 `127.0.0.1`，仅本机浏览器可访问
- **升级前自动备份数据库**到 `~/.trade/backups/`

> **免责声明**：文档中提及的 Alibaba、LinkedIn、Facebook、Instagram、TikTok、YouTube、WhatsApp 等均为其各自所有者的商标。本工具仅提供对这些平台数据的分析辅助，与上述平台无关联。制裁名单数据来源于 OFAC/UN/EU 公开数据，结果仅供参考，不构成法律意见。详见 [SECURITY.md](SECURITY.md)。

---

## 技术栈

- **AI 引擎**: [Hermes Agent](https://github.com/NousResearch/hermes-agent)（MIT 开源）
- **后端**: FastAPI + SQLite + uvicorn
- **前端**: 原生 JavaScript SPA（单文件，零构建工具依赖）
- **LLM**: 兼容 OpenAI / Anthropic / DeepSeek / MiniMax / Ollama 等
- **文档解析**: PyMuPDF / python-docx / openpyxl / python-pptx

---

## 项目结构

```
trade/                     B2B 业务层
├── api/                   FastAPI 路由（10 个业务域）
├── osint/                 客户背调模块（6 层检测）
├── skill_router.py        Skill 自动匹配引擎
├── skill_registry.py      14 个 skill 注册表（纯数据）
└── ... + 13 个业务模块

skills/                    14 个 B2B skills（Markdown 驱动）
tests/                     测试覆盖（database/business/api/osint/smoke）
server.py                  FastAPI 入口
```

---

## 开发

```bash
pip install -e ".[dev,docs]"
python -m pytest tests/ -v   # 运行测试
ruff check trade/ server.py  # 代码检查
```

## 文档

- [项目需求文档](项目需求文档.md) ([English](项目需求文档.en.md))
- [业务概览](业务概览.md) ([English](业务概览.en.md))
- [外贸业务知识库](外贸业务知识库.md) ([English](外贸业务知识库.en.md))
- [外贸业务方法总结](外贸业务方法总结.md) ([English](外贸业务方法总结.en.md))
- [Trade 数据目录结构设计](Trade数据目录结构设计.md) ([English](Trade数据目录结构设计.en.md))
- [使用说明书](使用说明书.md) ([English](使用说明书.en.md))
- [COMPATIBILITY.md](COMPATIBILITY.md) — Hermes 版本兼容性记录
- [数据库 Schema](docs/database-schema.md)

---

## 联系作者

<img src="docs/wechat-contact.jpeg" alt="WeChat Contact" width="200">

扫码添加微信，备注「Trade」。商务合作或技术支持请发邮件至 lauroge@gmail.com。

---

**Smart Trade AI** — 把重复劳动交给 AI，把时间留给客户。
