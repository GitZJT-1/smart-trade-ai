---
layout: default
---

<style>
  /* 全宽布局：覆盖 slate 主题的窄容器限制 */
  .container { max-width: 100% !important; padding: 0 2rem !important; }
  .container .content { max-width: 100% !important; }
  pre, code { white-space: pre-wrap !important; word-break: break-all !important; }
  pre { padding: 1rem !important; font-size: 0.9rem !important; }
</style>

<!-- Hero -->
<div style="text-align:center; padding:2rem 1rem 1rem;">
  <h1 style="font-size:2.4rem; margin-bottom:0.2em;">Smart Trade AI</h1>
  <p style="font-size:1.2rem; color:#58a6ff; margin:0;">外贸业务员的本地 AI 助手</p>
  <p style="color:#8b949e;">在本地运行，数据留在自己电脑里</p>
  <a href="https://github.com/chefroger/smart-trade-ai" class="btn btn-primary" style="margin:0.5rem;">View on GitHub</a>
  <a href="#windows-install" class="btn" style="margin:0.5rem;">Windows 安装 →</a>
</div>

---

<div style="text-align:center;">
  <img src="screenshot-2.png" alt="Customer & Cron Panel" style="max-width:75%; border-radius:8px; box-shadow:0 4px 24px rgba(0,0,0,.4);">
  <p><em>客户管理 + 定时任务面板</em></p>
</div>

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

<div style="text-align:center;">
  <img src="screenshot-1.png" alt="AI Chat Interface" style="max-width:75%; border-radius:8px; box-shadow:0 4px 24px rgba(0,0,0,.4);">
  <p><em>AI 对话界面 — 自动调用 web_search / read_file / database 工具</em></p>
</div>

---

## <a id="windows-install"></a>Windows 安装指南

> Windows 是最常见的使用平台，以下提供 3 种安装方式，按难度从低到高排列。

### 方式一：一键安装脚本（推荐）

只需提前安装 Python，其余全自动。

**Step 0 — 安装 Python**

从 [python.org](https://www.python.org/downloads/) 下载 **Python 3.11 ~ 3.13 Windows installer (64-bit)**。

> **必须勾选「Add Python to PATH」**，否则后续命令找不到 python。

安装完成后，**重新打开 PowerShell**，验证：

```powershell
python --version
# 应显示 Python 3.11.x 或更高
```

**Step 1 — 启用长路径支持（以管理员身份运行 PowerShell，仅需一次）**

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

> 执行后**需重启电脑**。不开启的话，后续 `pip install` 可能报 `Filename too long` 错误。

**Step 2 — 下载并运行安装脚本**

```powershell
irm https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.ps1 | iex
```

脚本自动完成：Python 检查 → 创建 venv → 安装 Hermes Agent → 安装 Trade → 15 个 skills → 数据库初始化 → 注册 `trade` 命令 → 设置开机自启动。

安装完成后，启动方式：

```powershell
trade                              # 新终端直接运行
# 或
python server.py                   # 在安装目录下
```

浏览器自动打开 http://127.0.0.1:9119/trade 。开机也会自动后台启动。

> **如果脚本执行报错**，可能是网络问题（GitHub 访问不稳定）。参考下方「网络注意事项」。

### 方式二：逐步手动安装

适合想控制每一步的用户，或者一键脚本失败后排查问题。

**前置条件**：Python >= 3.11（已加入 PATH）· 网络能访问 GitHub

```powershell
# 0. 启用长路径支持（管理员 PowerShell，仅需一次，执行后重启电脑）
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# 1. 安装 Hermes Agent（AI 引擎，自动处理 Node.js + Git + 依赖）
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex

# 2. 配置 LLM API Key
hermes setup
# 按提示选择 provider（推荐 DeepSeek），粘贴 API Key

# 3. 安装 Smart Trade AI
git clone --branch main https://github.com/chefroger/smart-trade-ai.git $env:LOCALAPPDATA\trade\foreign-trade-assistant
cd $env:LOCALAPPDATA\trade\foreign-trade-assistant
pip install -e "."
install-trade-skills

# 4. 启动
python server.py
# → 浏览器打开 http://127.0.0.1:9119/trade
```

> 如果第 3 步 `pip install` 报 `Filename too long`，说明长路径未生效，请确认第 0 步已完成并重启电脑。

### 方式三：打包为独立 EXE（双击运行，无需终端）

适合不想用终端的用户，或需要分发给同事。

```powershell
pip install pyinstaller
powershell -File scripts/build.ps1
# 生成 dist/Smart Trade AI.exe
```

双击 EXE 即可运行，无需 Python 环境。

### LLM API Key 配置

Smart Trade AI 需要 LLM API Key 才能工作。推荐方案：

| 方案 | 模型 | 适合场景 | 注册地址 |
|------|------|---------|---------|
| **推荐** | DeepSeek V4 Flash | 日常对话、文档分析、开发信 | [platform.deepseek.com](https://platform.deepseek.com) → 充值 → API Keys |

注册后获取 Key，运行 `hermes setup`，选择对应 provider 并填入即可。

> 还建议注册 [Tavily](https://tavily.com)（免费，每月 1000 次搜索），用于客户背调和实时信息检索。同样通过 `hermes setup` 配置。

### 网络注意事项

安装过程需要从 GitHub 克隆仓库并下载 Python 依赖。**境内用户请注意**：

- **建议全程开启 VPN（全局模式）**，否则 `git clone` 和 `pip install` 容易超时
- 如果 VPN 不稳定，可以多次重试安装命令，脚本支持断点续装
- VPN 代理未生效时，在 PowerShell 中手动设置：
  ```powershell
  $env:HTTPS_PROXY = "http://127.0.0.1:你的代理端口"
  ```

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| `python` 命令找不到 | 重新安装 Python，勾选「Add Python to PATH」，然后重新打开 PowerShell |
| `Filename too long` | 以管理员 PowerShell 执行长路径注册命令（见 Step 1），然后重启电脑 |
| `git clone` 超时 | 开启 VPN 全局模式；或设置 `$env:HTTPS_PROXY` |
| `pip install` 报红字 | 通常是网络问题，重试即可；确认 VPN 正常 |
| 升级后页面样式异常 | 按 `Ctrl+Shift+R` 强制刷新浏览器缓存 |

---

## macOS / Linux 安装

### 一键脚本

```bash
curl -fsSL https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh | bash
```

> 审查后执行：
> ```bash
> curl -fsSLO https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh
> less install.sh && bash install.sh
> ```

### 手动安装

```bash
# 1. 安装 Hermes Agent
git clone --branch main https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent && pip install -e "."

# 2. 配置 LLM
hermes setup

# 3. 安装 Smart Trade AI
git clone --branch main https://github.com/chefroger/smart-trade-ai.git ~/.trade/foreign-trade-assistant
cd ~/.trade/foreign-trade-assistant && pip install -e "."

# 4. 启动
install-trade-skills
python server.py
# → 浏览器打开 http://127.0.0.1:9119/trade
```

---

## 15 项专业能力

| 场景 | 能力 |
|------|------|
| 平台诊断 | 分析阿里国际站/中国制造网产品页面，输出优化建议 |
| 社媒营销 | 生成 Facebook/Instagram/TikTok/YouTube 内容日历 |
| LinkedIn 运营 | Profile 优化 + 内容策略 + InMail 模板 |
| 海关数据 | 分析进出口数据，筛选高价值采购商 |
| 客户开发 | 根据目标市场+产品生成开发信和跟进序列 |
| 客户管理 | A/B/C 分级、详情面板、文档库关联 |
| 文档分析 | 读取本地 PDF/Word/Excel/PPT，AI 自动解析 |
| 商务文档生成 | 一键生成报价单、PI、合同（DOCX/XLSX/PPTX） |
| 报价谈判 | 基于产品知识库和客户画像给出谈判策略 |
| 客户背调 | 6 层验证：邮箱→WHOIS→制裁→邮箱验证→技术栈→LinkedIn |
| 每日简报 | 实时汇率+大宗商品+市场新闻+客户跟进提醒 |
| 定时任务 | 工作日自动化：早报/开发信/社媒/每日总结 |
| 对话记录 | 按公司隔离的聊天记忆，支持搜索/回溯 |
| Skill 生成器 | 用自然语言描述需求，自动生成新 skill 并注册到系统 |

---

## 数据安全

- **业务数据默认存储在本地**（`~/.trade/`），不上传任何服务器
- 如使用 **Ollama 等本地模型**，可实现完整本地运行，数据完全不出电脑
- 如使用 **OpenAI / Anthropic / DeepSeek 等云端 LLM**，用户输入和必要上下文会发送至所选服务商——不包含客户身份信息
- 多公司数据隔离（`X-Company-ID` header）
- 绑定 `127.0.0.1`，仅本机浏览器可访问
- **升级前自动备份数据库**到 `~/.trade/backups/`

---

## 技术栈

| 层 | 技术 |
|----|------|
| AI 引擎 | [Hermes Agent](https://github.com/NousResearch/hermes-agent)（MIT 开源） |
| 后端 | FastAPI + SQLite + uvicorn |
| 前端 | 原生 JavaScript SPA（单文件，零构建工具依赖） |
| LLM | 兼容 OpenAI / Anthropic / DeepSeek / MiniMax / Ollama 等 |
| 文档解析 | PyMuPDF / python-docx / openpyxl / python-pptx |

---

## 联系作者

<div style="text-align:center;">
  <img src="wechat-contact.jpeg" alt="WeChat Contact" width="200" style="border-radius:8px;">
  <p>扫码添加微信，备注「Trade」</p>
  <p>商务合作或技术支持请发邮件至 <a href="mailto:lauroge@gmail.com">lauroge@gmail.com</a></p>
</div>

---

<p style="text-align:center; color:#8b949e;">
  Smart Trade AI — 外贸业务员的本地 AI 助手<br>
  <a href="https://github.com/chefroger/smart-trade-ai">GitHub</a> ·
  <a href="https://github.com/chefroger/smart-trade-ai/releases">Releases</a> ·
  <a href="https://github.com/chefroger/smart-trade-ai/blob/main/LICENSE">MIT License</a>
</p>
