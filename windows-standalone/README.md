# TradeWin — Windows 独立版

Foreign Trade Assistant 的 Windows 原生桌面应用。

## 系统要求

- Windows 10 (1903+) / Windows 11
- 4 GB RAM 以上
- 无需安装 Python — 单一 .exe 文件，双击运行

## 快速开始

1. 下载 `TradeWin.exe` 到任意目录
2. 双击运行
3. 首次启动自动弹出配置向导：
   - 选择 LLM 提供商（OpenAI / Claude / MiniMax / DeepSeek / Moonshot）
   - 输入 API Key（自动写入 `~/.hermes/.env`）
   - 自动安装 Trade Skills + 初始化数据库
4. 配置完成后即可使用，无需任何手动设置

## 功能

- 💬 AI 聊天 — 外贸销售助手，支持文档分析、报价生成、客户背调
  - SSE 流式响应，工具调用过程实时显示
  - 每条 AI 回复右上角附「📋 复制」按钮，一键写入剪贴板
  - `QTextCursor` 锚点增量更新，长回答下无重排卡顿
- 👥 客户管理 — 多公司隔离，客户 CRUD（A/B/C 等级、国家、最近跟进）
- 📁 文档库 — 列出当前公司所有文档库（名称/根目录/说明）
- 📋 任务面板 — Cron 定时任务自动化
- 🔑 许可证管理 — 试用/激活（Ed25519 签名 + 机器绑定）
- ⬆️ 一键更新 — git pull + pip install + skills 同步 + 数据库迁移 + 自动重启
- 🔄 公司切换 — 侧边栏下拉框切换，自动通知后端改绑 session

## 开发者构建

**方式 1：本地构建（需 Windows + Python 3.11+）**

```cmd
cd windows-standalone
build.bat
```

构建产物在 `dist/TradeWin.exe`（约 80-120 MB）。

**方式 2：GitHub Actions 自动构建（推荐）**

打 tag 触发自动构建，产物上传到 Releases 页面：

```bash
git tag v0.6.2
git push origin v0.6.2
```

构建流程定义在 `.github/workflows/build-tradewin.yml`，约 5-10 分钟完成。产物命名 `TradeWin-{version}.exe`，同时作为 workflow artifact 保留 30 天。

也可在 GitHub 仓库的 **Actions** 页面手动触发（`workflow_dispatch`）。

## 技术栈

- **GUI:** PySide6 (Qt6)
- **后端:** FastAPI + uvicorn (daemon thread)
- **AI:** Hermes Agent (NousResearch)
- **打包:** PyInstaller --onefile --windowed

## 已知限制

1. **Markdown 渲染**: QTextBrowser 仅支持 HTML 子集，复杂表格/代码块显示有限
2. **文件大小**: PyInstaller --onefile 打包后约 100MB+（含 Qt6 + Python 标准库）
3. **杀毒误报**: 无数字签名的 PyInstaller exe 可能被 Windows Defender 误报
