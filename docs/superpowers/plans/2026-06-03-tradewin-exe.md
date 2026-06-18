# TradeWin.exe — 独立 Windows 桌面应用 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 创建独立 Windows .exe，内嵌 WebView 加载现有 trade_chat.html，无需浏览器。

**Architecture:** Python + pywebview + 现有 FastAPI 后端。`tradewin.py` 启动脚本：初始化 Bootstrap → 创建 FastAPI app → 启动 uvicorn 线程 → 开 WebView 窗口指向 `http://127.0.0.1:9119/trade` → 窗口关闭时自动退出。PyInstaller 打包为单一 .exe。

**Tech Stack:** pywebview, PyInstaller, 现有 FastAPI + trade 代码

---

### Task 1: 添加依赖

- [ ] **Step 1: 将 pywebview 加入 pyproject.toml 可选依赖**

```toml
# pyproject.toml [project.optional-dependencies] 中新增:
desktop = [
    "pywebview>=5.0",
    "pyinstaller>=6.0",
]
```

- [ ] **Step 2: 安装依赖**

```bash
pip install pywebview
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: 添加 pywebview 桌面依赖"
```

---

### Task 2: 创建 tradewin.py 启动脚本

**Files:**
- Create: `tradewin.py`

- [ ] **Step 1: 写 tradewin.py**

```python
"""
TradeWin — 独立桌面应用入口。

双击 tradewin.exe 启动：FastAPI 后端 + WebView 窗口。
不依赖外部浏览器。
"""

import multiprocessing
import sys
import threading
import time

import uvicorn


def main():
    """启动后端 + 等待其就绪 + 打开 WebView 窗口。"""
    # 1. Bootstrap（路径、版本检查、env 加载、skills 同步）
    from trade.bootstrap import setup
    setup()

    # 2. 创建 FastAPI app
    from trade.app import create_app, serve_trade_chat

    host = "127.0.0.1"
    port = 9119

    app = create_app()
    serve_trade_chat(app)

    # 3. 启动 uvicorn 在后台线程
    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": host, "port": port, "log_level": "warning"},
        daemon=True,
    )
    server_thread.start()

    # 4. 等待后端就绪
    import urllib.request

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/status", timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    else:
        print("Error: 后端启动超时")
        sys.exit(1)

    # 5. 打开 WebView 窗口
    import webview

    url = f"http://{host}:{port}/trade"
    window = webview.create_window(
        "Smart Trade AI",
        url,
        width=1280,
        height=900,
        min_size=(900, 600),
        text_select=True,
    )

    # 窗口关闭后退出
    webview.start()
    sys.exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
```

- [ ] **Step 2: 本地运行验证**

```bash
python tradewin.py
```

期望：弹出 WebView 窗口，加载 Trade 界面，功能正常。

- [ ] **Step 3: Commit**

```bash
git add tradewin.py
git commit -m "feat: 添加 tradewin.py 独立桌面启动脚本"
```

---

### Task 3: 更新 Windows 打包脚本

**Files:**
- Modify: `scripts/build.ps1`

- [ ] **Step 1: 更新 build.ps1 入口点**

找到 `pyinstaller` 命令行部分，把入口点改为 `tradewin.py`，并添加 `--add-data` 包含 `static/` 目录：

```powershell
# 打包命令
pyinstaller `
    --name="Smart Trade AI" `
    --onefile `
    --windowed `
    --icon=static/favicon.ico `
    --add-data="static;static" `
    --add-data="skills;skills" `
    --add-data=".trade-template;.trade-template" `
    --hidden-import=trade.bootstrap `
    --hidden-import=trade.app `
    --hidden-import=trade.api `
    --hidden-import=trade.api.chat `
    --hidden-import=trade.api.companies `
    --hidden-import=trade.api.customers `
    --hidden-import=trade.api.libraries `
    --hidden-import=trade.api.orders `
    --hidden-import=trade.api.conversations `
    --hidden-import=trade.api.cron `
    --hidden-import=trade.api.memory `
    --hidden-import=trade.api.onboarding `
    --hidden-import=trade.api.deps `
    --hidden-import=trade.api.models `
    --hidden-import=trade.api.license `
    --hidden-import=trade.license `
    --hidden-import=trade.osint `
    --hidden-import=trade.osint.orchestrator `
    --hidden-import=trade.osint.whois `
    --hidden-import=trade.osint.email_verify `
    --hidden-import=trade.osint.sanctions `
    --hidden-import=trade.osint.tech_stack `
    --hidden-import=trade.osint.linkedin_verify `
    --hidden-import=trade.osint.scoring `
    --hidden-import=trade.osint.constants `
    --hidden-import=trade.skill_registry `
    --hidden-import=trade.skill_router `
    --hidden-import=trade.prompts `
    --hidden-import=trade.prompt `
    --hidden-import=trade.chat_memory `
    --hidden-import=trade.memory `
    --hidden-import=trade.onboarding `
    --hidden-import=trade.post_install `
    --hidden-import=trade.email_intel `
    --hidden-import=cryptography `
    tradewin.py
```

关键变化：
- `--name="Smart Trade AI"` → 输出 `Smart Trade AI.exe`
- `--windowed` → 不弹命令行窗口
- `--add-data` → 把 `static/`（含 `trade_chat.html`）、`skills/`、`.trade-template/` 打包进 exe
- 入口点从 `server.py` 改为 `tradewin.py`

- [ ] **Step 2: Commit**

```bash
git add scripts/build.ps1
git commit -m "build: Windows build 入口改为 tradewin.py（WebView 模式）"
```

---

### Task 4: 修复 PyInstaller 路径问题

PyInstaller 打包后 `__file__` 指向临时解压目录，需要处理几个路径问题：

- [ ] **Step 1: 修复 bootstrap.py 中的路径引用**

在 `trade/bootstrap.py` 的 `_adjust_sys_path()` 开头添加 PyInstaller 检测：

```python
def _adjust_sys_path():
    # PyInstaller 打包后 _MEIPASS 是临时解压目录
    if getattr(sys, 'frozen', False):
        return
    ...
```

- [ ] **Step 2: 修复 app.py 中 static/trade_chat.html 的路径**

在 `trade/app.py` 的 `serve_trade_chat()` 中：

```python
def serve_trade_chat(app):
    import sys
    if getattr(sys, 'frozen', False):
        _STATIC_DIR = Path(sys._MEIPASS) / "static"
    else:
        _STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
    _TRADE_CHAT_HTML = _STATIC_DIR / "trade_chat.html"
    ...
```

- [ ] **Step 3: 修复 bootstrap.py 中 skills 同步的路径**

在 `trade/bootstrap.py` 的 `sync_b2b_skills()` 中，PyInstaller 模式下：

```python
if getattr(sys, 'frozen', False):
    _project_root = Path(sys._MEIPASS)
else:
    _project_root = Path(__file__).resolve().parent.parent
```

- [ ] **Step 4: 本地打包测试**

```bash
pyinstaller --onefile --windowed --add-data="static:static" --add-data="skills:skills" --add-data=".trade-template:.trade-template" --hidden-import=trade.bootstrap --hidden-import=trade.app --hidden-import=trade.api --hidden-import=cryptography tradewin.py
```

验证 `dist/tradewin.exe` 能正常启动。

- [ ] **Step 5: Commit**

```bash
git add trade/bootstrap.py trade/app.py
git commit -m "fix: PyInstaller 打包路径兼容（_MEIPASS）"
```

---

### Task 5: 生成 favicon.ico

- [ ] **Step 1: 用 Python 生成简单 ico 文件**

```bash
python -c "
from PIL import Image
img = Image.new('RGBA', (64, 64), (59, 130, 246, 255))
img.save('static/favicon.ico', format='ICO', sizes=[(64, 64)])
print('favicon.ico created')
"
```

如果没有 PIL：`pip install Pillow`

- [ ] **Step 2: Commit**

```bash
git add static/favicon.ico
git commit -m "feat: 添加桌面应用图标"
```

---

### 文件变更总览

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `tradewin.py` | 桌面启动脚本（约 60 行） |
| 修改 | `pyproject.toml` | 添加 `[desktop]` 可选依赖 |
| 修改 | `scripts/build.ps1` | 入口改为 `tradewin.py` |
| 修改 | `trade/bootstrap.py` | PyInstaller `_MEIPASS` 路径兼容 |
| 修改 | `trade/app.py` | PyInstaller `_MEIPASS` 路径兼容 |
| 新建 | `static/favicon.ico` | 应用图标 |

**共 6 个文件变更，约 80 行新代码。**
