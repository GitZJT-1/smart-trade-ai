# TradeWin Standalone — Windows 独立版实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建单一 .exe 可执行文件（双击运行），包含 Trade 全部功能，使用 Windows 原生 GUI（PySide6 Qt），仅在 Windows 10/11 下运行。

**Architecture:** FastAPI 后端在 daemon 线程中运行于 localhost:9119，PySide6 GUI 通过 HTTP 与后端通信。所有现有 `trade/` 包代码零修改复用。PyInstaller `--onefile --windowed` 打包为单一 .exe。

**Tech Stack:** Python 3.11+, PySide6 (Qt6), FastAPI, uvicorn, PyInstaller, QTextBrowser (Markdown), Windows Task Scheduler (开机自启)

---

## 文件结构

```
windows-standalone/
├── tradewin/
│   ├── __init__.py          # 包入口
│   ├── app.py               # QApplication + 主窗口 + 侧边栏
│   ├── chat.py              # 聊天视图（Markdown 渲染 + SSE 流式）
│   ├── dialogs.py           # 模态对话框（公司/客户/文档库/设置/激活）
│   ├── tasks.py             # Cron 任务面板
│   ├── api.py               # HTTP 客户端封装（与本地 FastAPI 通信）
│   ├── tray.py              # 系统托盘图标 + 右键菜单
│   ├── themes.py            # Qt 样式表（亮/暗主题）
│   ├── main.py              # 入口：启动 FastAPI 线程 → 启动 Qt GUI
│   └── resources/
│       ├── icon.ico         # 应用图标
│       └── style.qss        # Qt 样式表
├── tradewin.spec            # PyInstaller 打包配置
├── build.bat                # Windows 构建脚本
└── requirements.txt         # 独立依赖（仅 Windows 需要的额外包）
```

**零修改复用:**
- `trade/api/*` — 全部 API 端点
- `trade/database.py` — SQLite 层
- `trade/company.py` — 公司 CRUD
- `trade/osint/*` — 背调引擎
- `trade/prompt.py` — 系统提示词
- `trade/skill_router.py` — 技能路由
- `trade/post_install/*` — 更新/备份
- `static/trade_chat.html` — 不再使用（GUI 替代）

---

### Task 1: 项目骨架 + 依赖配置

**Files:**
- Create: `windows-standalone/requirements.txt`
- Create: `windows-standalone/tradewin/__init__.py`
- Create: `windows-standalone/tradewin/main.py`
- Create: `windows-standalone/tradewin/resources/icon.ico`

- [ ] **Step 1: 编写 requirements.txt**

```txt
# 注意：此文件仅包含 Windows 独立版 EXTRA 依赖
# 核心依赖（fastapi/uvicorn/hermes-agent 等）由父项目 pyproject.toml 管理
PySide6>=6.7.0,<7.0
pyinstaller>=6.0,<7.0
```

- [ ] **Step 2: 创建包入口 __init__.py**

```python
"""
TradeWin — Foreign Trade Assistant Windows 独立桌面版。

使用 PySide6 (Qt6) 构建原生 Windows GUI，
FastAPI 后端在后台线程运行，GUI 通过 HTTP 与后端通信。
"""
```

- [ ] **Step 3: 创建 main.py 骨架（验证 FastAPI 线程 + Qt 启动）**

```python
"""
TradeWin 入口：启动 FastAPI 后台线程 → 初始化 Qt Application → 进入事件循环。
"""

import sys
import threading
from pathlib import Path

# 将父项目根目录加入 sys.path，使 trade 包可导入
_parent = Path(__file__).resolve().parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from PySide6.QtWidgets import QApplication


def _start_backend() -> None:
    """在 daemon 线程中启动 FastAPI 服务（localhost:9119）。"""
    import uvicorn
    from trade.app import create_app, serve_trade_chat, _install_cors

    app = create_app()
    serve_trade_chat(app)
    _install_cors(app, 9119)
    uvicorn.run(app, host="127.0.0.1", port=9119, log_level="warning")


def main() -> None:
    """主入口：启动后端 → 启动 Qt GUI。"""
    # 1) 后台线程启动 FastAPI
    _thread = threading.Thread(target=_start_backend, daemon=True)
    _thread.start()

    # 2) 初始化 Qt Application
    _qt_app = QApplication(sys.argv)
    _qt_app.setApplicationName("TradeWin")
    _qt_app.setOrganizationName("SmartTradeAI")

    # 3) TODO: 创建主窗口并显示（后续 Task）

    # 4) 进入 Qt 事件循环
    sys.exit(_qt_app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 生成应用图标（占位 ico 文件）**

```bash
# 用 Python 生成最小可用的 ico（后续替换为正式图标）
python3 -c "
from pathlib import Path
# 写一个最小的 1x1 透明 ico 占位文件
ico = bytes([
    0,0,1,0,1,0,1,1,0,0,1,0,24,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,255,255,255,0
])
Path('windows-standalone/tradewin/resources/icon.ico').write_bytes(ico)
"
```

- [ ] **Step 5: 验证 main.py 可导入**

```bash
cd windows-standalone && python3 -c "from tradewin.main import main; print('OK')"
```
Expected: OK (或 FastAPI 未安装的 ImportError，正常——Windows 上装完依赖后解决)

- [ ] **Step 6: Commit**

```bash
git add windows-standalone/
git commit -m "feat: TradeWin 骨架 — main.py + requirements + 项目结构"
```

---

### Task 2: API 客户端封装

**Files:**
- Create: `windows-standalone/tradewin/api.py`

- [ ] **Step 1: 编写 api.py（HTTP 客户端，封装所有 API 调用）**

```python
"""
TradeWin — 本地 FastAPI HTTP 客户端。

封装所有与 localhost:9119 的 API 通信，统一处理 session token、company header。
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error

_BASE = "http://127.0.0.1:9119"
_session_token: str = ""  # 首次 /api/status 时自动获取
_company_id: str = ""     # 当前选中的公司 ID


def set_company(cid: str) -> None:
    """切换当前公司（所有后续请求携带 X-Company-ID header）。"""
    global _company_id
    _company_id = cid


def _get(path: str) -> dict | None:
    """GET 请求，返回 JSON dict 或 None（网络错误时）。"""
    url = f"{_BASE}{path}"
    req = urllib.request.Request(url)
    if _session_token:
        req.add_header("X-Hermes-Session-Token", _session_token)
    if _company_id:
        req.add_header("X-Company-ID", _company_id)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _post(path: str, body: dict | None = None) -> dict | None:
    """POST 请求，返回 JSON dict 或 None。"""
    url = f"{_BASE}{path}"
    data = json.dumps(body).encode() if body else b"{}"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if _session_token:
        req.add_header("X-Hermes-Session-Token", _session_token)
    if _company_id:
        req.add_header("X-Company-ID", _company_id)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


# ── 公开 API 函数 ──────────────────────────────────────────────────────────

def init_session() -> dict | None:
    """从 /api/status 获取 session token（注入 HTML 中，需解析）。"""
    global _session_token
    url = f"{_BASE}/trade"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode()
            # 从 HTML 中提取 __TRADE_SESSION_TOKEN__
            import re
            m = re.search(r"__TRADE_SESSION_TOKEN__\s*=\s*'([^']+)'", html)
            if m:
                _session_token = m.group(1)
                return {"ok": True}
    except Exception:
        pass
    return None


def get_status() -> dict | None:
    """GET /api/status — 版本检查 + 健康状态。"""
    return _get("/api/status")


def list_companies() -> list[dict]:
    """GET /api/trade/companies — 公司列表（脱敏版）。"""
    r = _get("/api/trade/companies")
    if r and isinstance(r, list):
        return r
    return []


def create_company(name: str) -> dict | None:
    """POST /api/trade/companies — 创建公司。"""
    return _post("/api/trade/companies", {"name": name})


def list_customers() -> list[dict]:
    """GET /api/trade/customers — 客户列表。"""
    r = _get("/api/trade/customers")
    if r and isinstance(r, list):
        return r
    return []


def list_libraries() -> list[dict]:
    """GET /api/trade/libraries — 文档库列表。"""
    r = _get("/api/trade/libraries")
    if r and isinstance(r, list):
        return r
    return []


def send_chat(query: str, library_id: int | None = None) -> dict | None:
    """POST /api/trade/chat — 同步聊天。"""
    body = {"query": query}
    if library_id:
        body["library_id"] = library_id
    return _post("/api/trade/chat", body)


def stream_chat(query: str, on_event, library_id: int | None = None) -> None:
    """POST /api/trade/chat/stream — SSE 流式聊天。

    on_event(event_type: str, data: dict) 回调在收到每个 SSE 事件时调用。
    事件类型: tool_start, tool_complete, thinking, response, error, done。
    """
    import urllib.request as _ur

    body = {"query": query}
    if library_id:
        body["library_id"] = library_id
    data = json.dumps(body).encode()

    url = f"{_BASE}/api/trade/chat/stream"
    req = _ur.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    if _session_token:
        req.add_header("X-Hermes-Session-Token", _session_token)
    if _company_id:
        req.add_header("X-Company-ID", _company_id)

    try:
        with _ur.urlopen(req, timeout=600) as resp:  # 10分钟超时
            buf = ""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buf += chunk.decode()
                while "\n\n" in buf:
                    event_str, buf = buf.split("\n\n", 1)
                    for line in event_str.split("\n"):
                        if line.startswith("event: "):
                            etype = line[7:]
                        elif line.startswith("data: "):
                            try:
                                edata = json.loads(line[6:])
                                on_event(etype, edata)
                            except json.JSONDecodeError:
                                pass
    except Exception as e:
        on_event("error", {"message": str(e)})


def get_license_status() -> dict | None:
    """GET /api/trade/license/status — 许可证状态。"""
    return _get("/api/trade/license/status")


def activate_license(code: str) -> dict | None:
    """POST /api/trade/license/activate — 激活许可证。"""
    return _post("/api/trade/license/activate", {"code": code})


def system_update() -> dict | None:
    """POST /api/trade/system/update — 一键更新系统。"""
    return _post("/api/trade/system/update")


def system_restart() -> dict | None:
    """POST /api/trade/system/restart — 重启服务。"""
    return _post("/api/trade/system/restart")
```

- [ ] **Step 2: Commit**

```bash
git add windows-standalone/tradewin/api.py
git commit -m "feat: API 客户端封装 — 所有后端接口的同步 HTTP 调用"
```

---

### Task 3: Qt 主题 + 样式系统

**Files:**
- Create: `windows-standalone/tradewin/themes.py`
- Create: `windows-standalone/tradewin/resources/style.qss`

- [ ] **Step 1: 编写 themes.py（Qt 调色板定义）**

```python
"""
TradeWin — Qt 主题系统。

定义亮色/暗色两套调色板，通过 Fusion style + QSS 实现现代化 Windows 原生外观。
"""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


def _load_qss() -> str:
    """加载 Qt 样式表（QSS 文件）。"""
    from pathlib import Path
    qss_file = Path(__file__).parent / "resources" / "style.qss"
    if qss_file.exists():
        return qss_file.read_text(encoding="utf-8")
    return ""


# ── 颜色常量（与现有 trade_chat.html CSS 变量对齐） ──────────────────────

PRIMARY = QColor("#3B82F6")
PRIMARY_DARK = QColor("#2563EB")
ACCENT = QColor("#F59E0B")
ACCENT_GREEN = QColor("#10B981")
ACCENT_RED = QColor("#EF4444")

BG_MAIN = QColor("#F1F5F9")
BG_CARD = QColor("#FFFFFF")
BG_INPUT = QColor("#F8FAFC")
BG_SIDEBAR = QColor("#0F172A")

TEXT_PRIMARY = QColor("#1E293B")
TEXT_SECONDARY = QColor("#64748B")
SIDEBAR_TEXT = QColor("#94A3B8")

BORDER = QColor("#E2E8F0")


def apply_theme(app: QApplication, dark: bool = False) -> None:
    """应用主题到 QApplication。

    Args:
        app: QApplication 实例
        dark: True = 暗色主题，False = 亮色主题（默认）
    """
    app.setStyle("Fusion")

    if dark:
        _apply_dark_palette(app)
    else:
        _apply_light_palette(app)

    # 加载自定义 QSS（微调 Qt widget 外观）
    qss = _load_qss()
    if qss:
        app.setStyleSheet(qss)


def _apply_light_palette(app: QApplication) -> None:
    """应用亮色主题调色板。"""
    p = QPalette()
    p.setColor(QPalette.Window, BG_MAIN)
    p.setColor(QPalette.WindowText, TEXT_PRIMARY)
    p.setColor(QPalette.Base, BG_CARD)
    p.setColor(QPalette.AlternateBase, BG_INPUT)
    p.setColor(QPalette.Text, TEXT_PRIMARY)
    p.setColor(QPalette.Button, BG_CARD)
    p.setColor(QPalette.ButtonText, TEXT_PRIMARY)
    p.setColor(QPalette.Highlight, PRIMARY)
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(p)


def _apply_dark_palette(app: QApplication) -> None:
    """应用暗色主题调色板。"""
    dark_bg = QColor("#1E293B")
    dark_card = QColor("#0F172A")
    dark_text = QColor("#E2E8F0")

    p = QPalette()
    p.setColor(QPalette.Window, dark_bg)
    p.setColor(QPalette.WindowText, dark_text)
    p.setColor(QPalette.Base, dark_card)
    p.setColor(QPalette.AlternateBase, QColor("#1E293B"))
    p.setColor(QPalette.Text, dark_text)
    p.setColor(QPalette.Button, dark_card)
    p.setColor(QPalette.ButtonText, dark_text)
    p.setColor(QPalette.Highlight, PRIMARY)
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(p)
```

- [ ] **Step 2: 编写 style.qss（微调样式）**

```css
/* TradeWin QSS Stylesheet — 微调 Qt Fusion 外观 */
QMainWindow { background: #F1F5F9; }
QToolBar { border: none; spacing: 4px; }
QStatusBar { background: #FFFFFF; border-top: 1px solid #E2E8F0; color: #64748B; font-size: 12px; }
QMenuBar { background: #FFFFFF; border-bottom: 1px solid #E2E8F0; }
QMenuBar::item:selected { background: #EFF6FF; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #E2E8F0; width: 1px; }
QTextBrowser { border: none; background: transparent; }
QLineEdit { border: 1px solid #E2E8F0; border-radius: 4px; padding: 6px 10px; background: #FFFFFF; }
QLineEdit:focus { border-color: #3B82F6; }
QPushButton { border: 1px solid #E2E8F0; border-radius: 4px; padding: 6px 12px; background: #FFFFFF; color: #1E293B; }
QPushButton:hover { background: #F8FAFC; border-color: #CBD5E1; }
QPushButton:pressed { background: #F1F5F9; }
QPushButton#primary { background: #3B82F6; color: #FFFFFF; border: none; font-weight: bold; }
QPushButton#primary:hover { background: #2563EB; }
QPushButton#danger { background: #EF4444; color: #FFFFFF; border: none; }
QPushButton#danger:hover { background: #DC2626; }
QComboBox { border: 1px solid #E2E8F0; border-radius: 4px; padding: 6px 10px; background: #FFFFFF; }
QComboBox:focus { border-color: #3B82F6; }
QComboBox::drop-down { border: none; }
QTreeWidget { border: 1px solid #E2E8F0; border-radius: 4px; background: #FFFFFF; alternate-background-color: #F8FAFC; }
QTreeWidget::item { padding: 4px 8px; }
QTreeWidget::item:selected { background: #EFF6FF; color: #1E293B; }
QTabWidget::pane { border: 1px solid #E2E8F0; border-radius: 4px; }
QTabBar::tab { padding: 8px 16px; border: 1px solid transparent; }
QTabBar::tab:selected { background: #FFFFFF; border-bottom: 2px solid #3B82F6; }
```

- [ ] **Step 3: Commit**

```bash
git add windows-standalone/tradewin/themes.py windows-standalone/tradewin/resources/style.qss
git commit -m "feat: Qt 主题系统 — 亮色/暗色调色板 + QSS 样式表"
```

---

### Task 4: 主窗口 + 侧边栏

**Files:**
- Create: `windows-standalone/tradewin/app.py`

- [ ] **Step 1: 编写 app.py（主窗口 + 侧边栏 + 视图路由）**

```python
"""
TradeWin — 主窗口。

布局: QSplitter
  ├── 左侧 QTreeWidget（侧边栏导航 + 公司选择器）
  └── 右侧 QStackedWidget（chat/customers/libraries/tasks/settings 视图）

每个视图是独立的 QWidget，通过 QStackedWidget 切换。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QComboBox, QWidget, QVBoxLayout, QLabel,
    QStatusBar, QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtGui import QAction

from tradewin.themes import PRIMARY_DARK
from tradewin.api import list_companies, set_company, init_session, get_status


class MainWindow(QMainWindow):
    """TradeWin 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TradeWin — 外贸智能助手")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        # ── 初始化 session token ────────────────────────────────────────
        self._init_session()

        # ── 中央区域：分割器 ────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self._splitter)

        # ── 左侧边栏 ────────────────────────────────────────────────────
        self._sidebar = self._build_sidebar()
        self._splitter.addWidget(self._sidebar)
        self._splitter.setSizes([250, 950])  # 侧边栏 250px，内容区 950px

        # ── 右侧视图栈 ──────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._splitter.addWidget(self._stack)

        # 注册视图（占位，后续 Task 替换为实际内容）
        self._chat_view = QLabel("Chat View")
        self._customers_view = QLabel("Customers View")
        self._libraries_view = QLabel("Libraries View")
        self._tasks_view = QLabel("Tasks View")
        self._settings_view = QLabel("Settings View")

        self._stack.addWidget(self._chat_view)       # index 0
        self._stack.addWidget(self._customers_view)   # index 1
        self._stack.addWidget(self._libraries_view)   # index 2
        self._stack.addWidget(self._tasks_view)       # index 3
        self._stack.addWidget(self._settings_view)    # index 4

        # 默认显示聊天视图
        self._stack.setCurrentIndex(0)

        # ── 状态栏 ──────────────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._version_label = QLabel("v?.?.?")
        self._status_bar.addPermanentWidget(self._version_label)

        # ── 加载公司列表 + 版本检查 ─────────────────────────────────────
        self._load_companies()
        self._check_version()

    # ── 内部方法 ──────────────────────────────────────────────────────────

    def _init_session(self) -> None:
        """连接到本地 Trade 后端，获取 session token。"""
        result = init_session()
        if result is None:
            QMessageBox.warning(
                self, "连接失败",
                "无法连接到本地 Trade 服务 (127.0.0.1:9119)。\n"
                "请确认服务已启动。"
            )

    def _build_sidebar(self) -> QWidget:
        """构建左侧导航栏。"""
        container = QWidget()
        container.setStyleSheet(
            f"background: {PRIMARY_DARK.name()}; border: none;"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 公司选择器
        self._company_combo = QComboBox()
        self._company_combo.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.1); color: #E2E8F0; "
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; "
            "padding: 6px 10px; margin: 8px; }"
            "QComboBox QAbstractItemView { background: #1E293B; color: #E2E8F0; }"
        )
        self._company_combo.currentIndexChanged.connect(self._on_company_changed)
        layout.addWidget(self._company_combo)

        # 导航树
        self._nav_tree = QTreeWidget()
        self._nav_tree.setHeaderHidden(True)
        self._nav_tree.setStyleSheet(
            "QTreeWidget { background: transparent; border: none; color: #94A3B8; "
            "font-size: 14px; }"
            "QTreeWidget::item { padding: 8px 12px; }"
            "QTreeWidget::item:selected { background: rgba(59,130,246,0.2); color: #FFFFFF; }"
        )

        # 导航项
        chat_item = QTreeWidgetItem(["💬 聊天"])
        chat_item.setData(0, Qt.UserRole, 0)  # stack index
        self._nav_tree.addTopLevelItem(chat_item)

        customers_item = QTreeWidgetItem(["👥 客户管理"])
        customers_item.setData(0, Qt.UserRole, 1)
        self._nav_tree.addTopLevelItem(customers_item)

        lib_item = QTreeWidgetItem(["📁 文档库"])
        lib_item.setData(0, Qt.UserRole, 2)
        self._nav_tree.addTopLevelItem(lib_item)

        tasks_item = QTreeWidgetItem(["📋 任务面板"])
        tasks_item.setData(0, Qt.UserRole, 3)
        self._nav_tree.addTopLevelItem(tasks_item)

        settings_item = QTreeWidgetItem(["⚙️ 设置"])
        settings_item.setData(0, Qt.UserRole, 4)
        self._nav_tree.addTopLevelItem(settings_item)

        self._nav_tree.itemClicked.connect(self._on_nav_clicked)
        self._nav_tree.setCurrentItem(chat_item)  # 默认选中聊天
        layout.addWidget(self._nav_tree)

        return container

    def _on_nav_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        """导航项点击 → 切换右侧视图。"""
        idx = item.data(0, Qt.UserRole)
        if idx is not None:
            self._stack.setCurrentIndex(idx)

    def _on_company_changed(self, index: int) -> None:
        """公司选择器切换 → 更新 API client 的公司上下文。"""
        cid = self._company_combo.itemData(index)
        if cid:
            set_company(str(cid))

    def _load_companies(self) -> None:
        """加载公司列表到下拉框。"""
        companies = list_companies()
        self._company_combo.clear()
        for c in companies:
            self._company_combo.addItem(
                f"{'🟢 ' if c.get('is_active') else '⚫ '}{c['name']}",
                c["id"]
            )

    def _check_version(self) -> None:
        """获取版本号并显示在状态栏。"""
        status = get_status()
        if status:
            self._version_label.setText(
                f"v{status.get('version', '?.?.?')}"
            )
            # 检查更新提示
            latest = status.get("latest_version")
            if latest and status.get("version") != latest:
                self._status_bar.showMessage(
                    f"新版本 {latest} 可用！点击 ⚙️ 设置 → 系统更新"
                )

    def get_stack(self) -> QStackedWidget:
        """返回视图栈（供各模块替换占位 view）。"""
        return self._stack
```

- [ ] **Step 2: 更新 main.py — 创建并显示 MainWindow**

```python
# 在 main.py 中，替换 TODO 注释：
from tradewin.app import MainWindow
from tradewin.themes import apply_theme

# 2) 初始化 Qt Application
_qt_app = QApplication(sys.argv)
_qt_app.setApplicationName("TradeWin")
_qt_app.setOrganizationName("SmartTradeAI")
apply_theme(_qt_app)  # 应用主题

# 3) 创建并显示主窗口
_window = MainWindow()
_window.show()

# 4) 进入 Qt 事件循环
sys.exit(_qt_app.exec())
```

- [ ] **Step 3: Commit**

```bash
git add windows-standalone/tradewin/app.py windows-standalone/tradewin/main.py
git commit -m "feat: 主窗口 + 侧边栏导航 + 公司选择器 + 版本状态栏"
```

---

### Task 5: 聊天视图（Markdown + SSE 流式）

**Files:**
- Create: `windows-standalone/tradewin/chat.py`

- [ ] **Step 1: 编写 chat.py**

```python
"""
TradeWin — 聊天视图。

功能：
  - 顶部：聊天上下文标签 + 清空/新建按钮
  - 中部：QTextBrowser Markdown 消息列表
  - 底部：QLineEdit 输入框 + 发送按钮
  - SSE 流式：逐字追加到当前 AI 消息气泡
"""

import json
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QLineEdit, QPushButton, QLabel, QScrollBar,
)
from PySide6.QtGui import QFont, QTextCursor

from tradewin.api import stream_chat, send_chat


# ── SSE Worker 线程 ───────────────────────────────────────────────────────

class ChatStreamWorker(QThread):
    """在后台线程中执行 SSE 流式聊天请求，通过 signal 投递事件到主线程。"""

    event_received = Signal(str, str)  # (event_type, json_data)

    def __init__(self, query: str, library_id: int | None = None):
        super().__init__()
        self._query = query
        self._library_id = library_id

    def run(self) -> None:
        def _on_event(etype: str, data: dict) -> None:
            self.event_received.emit(etype, json.dumps(data, ensure_ascii=False))

        stream_chat(self._query, _on_event, library_id=self._library_id)


# ── 聊天视图 ──────────────────────────────────────────────────────────────

class ChatView(QWidget):
    """TradeWin 聊天主界面。"""

    def __init__(self):
        super().__init__()
        self._response_buffer = ""  # SSE 累积中的 AI 回复文本

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── 消息显示区 ──────────────────────────────────────────────────
        self._msg_browser = QTextBrowser()
        self._msg_browser.setOpenExternalLinks(True)
        self._msg_browser.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self._msg_browser, 1)  # stretch=1，占据剩余空间

        # ── 输入区域 ────────────────────────────────────────────────────
        input_layout = QHBoxLayout()

        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("输入您的外贸问题...")
        self._input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self._input_field, 1)

        send_btn = QPushButton("发送")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

    # ── 消息发送 ──────────────────────────────────────────────────────────

    def _send_message(self) -> None:
        """发送用户消息，启动 SSE 流式接收。"""
        query = self._input_field.text().strip()
        if not query:
            return

        # 1) 显示用户消息
        self._append_message("🧑 您", query)

        # 2) 清空输入框 + 禁用
        self._input_field.clear()
        self._input_field.setEnabled(False)

        # 3) 插入 AI 消息占位
        self._response_buffer = ""
        self._msg_browser.moveCursor(QTextCursor.End)
        self._msg_browser.insertHtml(
            '<div style="margin:8px 0; padding:10px 14px; '
            'background:#F0FDF4; border-radius:8px;">'
            '<b style="color:#166534;">🤖 Trade AI</b><br>'
            '<span id="ai-response">⏳ 思考中...</span></div>'
        )
        self._scroll_to_bottom()

        # 4) 启动 SSE 后台线程
        self._worker = ChatStreamWorker(query)
        self._worker.event_received.connect(self._on_sse_event)
        self._worker.finished.connect(self._on_stream_done)
        self._worker.start()

    # ── SSE 事件处理 ──────────────────────────────────────────────────────

    def _on_sse_event(self, etype: str, data_str: str) -> None:
        """处理 SSE 事件（在主线程中执行）。"""
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return

        if etype == "response":
            chunk = data.get("content", "")
            self._response_buffer += chunk
            self._update_ai_message(self._response_buffer)
        elif etype == "tool_start":
            tool_name = data.get("tool", "unknown")
            self._append_status(f"🔧 调用工具: {tool_name}")
        elif etype == "tool_complete":
            tool_name = data.get("tool", "unknown")
            self._append_status(f"✅ 工具完成: {tool_name}")
        elif etype == "thinking":
            self._append_status("💭 思考中...")
        elif etype == "error":
            self._append_status(f"❌ {data.get('message', '未知错误')}")

    def _on_stream_done(self) -> None:
        """SSE 流结束 → 恢复输入框。"""
        self._input_field.setEnabled(True)
        self._input_field.setFocus()

    # ── UI 辅助 ───────────────────────────────────────────────────────────

    def _append_message(self, sender: str, content: str) -> None:
        """追加一条完整消息到消息浏览器。"""
        self._msg_browser.moveCursor(QTextCursor.End)
        bg = "#EFF6FF" if "您" in sender else "#F0FDF4"
        color = "#1E40AF" if "您" in sender else "#166534"
        text = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._msg_browser.insertHtml(
            f'<div style="margin:8px 0; padding:10px 14px; '
            f'background:{bg}; border-radius:8px;">'
            f'<b style="color:{color};">{sender}</b><br>'
            f'{text}</div>'
        )
        self._scroll_to_bottom()

    def _update_ai_message(self, content: str) -> None:
        """更新最后一条 AI 消息的内容（用于 SSE 增量渲染）。"""
        cursor = self._msg_browser.textCursor()
        cursor.movePosition(QTextCursor.End)
        # 找到 <span id="ai-response"> 并替换
        html = self._msg_browser.toHtml()
        text = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("\n", "<br>")
        html = html.replace(
            '<span id="ai-response">⏳ 思考中...</span>',
            f'<span id="ai-response">{text}</span>'
        )
        # HACK: toHtml()/setHtml() 对于大文本性能不佳，简化处理
        # 生产代码应使用 QTextDocument 操作
        self._msg_browser.setHtml(html)
        self._scroll_to_bottom()

    def _append_status(self, msg: str) -> None:
        """追加状态消息（工具调用/思考过程）。"""
        self._msg_browser.moveCursor(QTextCursor.End)
        self._msg_browser.insertHtml(
            f'<div style="margin:4px 0; color:#64748B; font-size:12px;">'
            f'{msg}</div>'
        )
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """滚动消息浏览器到底部。"""
        sb = self._msg_browser.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
```

- [ ] **Step 2: 在 app.py 中替换 chat 占位 view**

```python
# 在 MainWindow.__init__ 中，替换:
from tradewin.chat import ChatView
self._chat_view = ChatView()
# 替换原来的 QLabel("Chat View")
```

- [ ] **Step 3: Commit**

```bash
git add windows-standalone/tradewin/chat.py windows-standalone/tradewin/app.py
git commit -m "feat: 聊天视图 — Markdown 消息显示 + SSE 流式增量渲染"
```

---

### Task 6: 系统托盘 + 后台运行

**Files:**
- Create: `windows-standalone/tradewin/tray.py`

- [ ] **Step 1: 编写 tray.py**

```python
"""
TradeWin — 系统托盘图标。

功能：
  - 托盘图标（应用 icon.ico）
  - 右键菜单：显示主窗口 / 退出
  - 双击托盘图标 → 显示主窗口
  - 关闭窗口 → 最小化到托盘（不退出）
"""

from pathlib import Path

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


class TrayManager:
    """系统托盘管理器。"""

    def __init__(self, app: QApplication, main_window):
        self._app = app
        self._main_window = main_window

        # 加载图标
        icon_path = Path(__file__).parent / "resources" / "icon.ico"
        icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()

        # 创建托盘
        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip("TradeWin — 外贸智能助手")

        # 右键菜单
        menu = QMenu()
        show_action = QAction("📋 显示主窗口")
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("❌ 退出")
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

        # 双击托盘 → 显示窗口
        self._tray.activated.connect(self._on_activated)

        self._tray.show()

    def _show_window(self) -> None:
        """显示主窗口并激活到前台。"""
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盘图标激活事件。"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _quit(self) -> None:
        """完全退出应用。"""
        self._app.quit()

    def show_notification(self, title: str, message: str) -> None:
        """显示 Windows 通知气泡。"""
        self._tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)
```

- [ ] **Step 2: 在 main.py 中集成托盘**

```python
from tradewin.tray import TrayManager

# 创建托盘
_tray = TrayManager(_qt_app, _window)

# 关闭窗口 → 最小化到托盘
def _close_to_tray(event):
    event.ignore()
    _window.hide()
    _tray.show_notification("TradeWin", "已最小化到系统托盘")
_window.closeEvent = _close_to_tray
```

- [ ] **Step 3: Commit**

```bash
git add windows-standalone/tradewin/tray.py windows-standalone/tradewin/main.py
git commit -m "feat: 系统托盘 — 最小化到托盘 + 右键菜单 + 通知气泡"
```

---

### Task 7: 模态对话框（公司/客户/文档库/设置/激活）

**Files:**
- Create: `windows-standalone/tradewin/dialogs.py`

- [ ] **Step 1: 编写 dialogs.py**

```python
"""
TradeWin — 模态对话框集合。

包含：公司管理、客户管理、文档库管理、设置、许可证激活。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout,
    QMessageBox, QTextEdit, QTabWidget, QWidget,
)
from PySide6.QtGui import QFont

from tradewin.api import (
    list_companies, create_company, list_customers, list_libraries,
    get_license_status, activate_license, system_update, system_restart,
)


# ── 公司管理对话框 ────────────────────────────────────────────────────────

class CompanyDialog(QDialog):
    """公司选择 + 创建对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("公司管理")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 公司列表
        self._list = QListWidget()
        self._refresh_list()
        layout.addWidget(QLabel("现有公司:"))
        layout.addWidget(self._list)

        # 新建公司
        hl = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("输入新公司名称...")
        hl.addWidget(self._name_input)

        create_btn = QPushButton("创建")
        create_btn.setObjectName("primary")
        create_btn.clicked.connect(self._create_company)
        hl.addWidget(create_btn)
        layout.addLayout(hl)

        # 关闭
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_list(self) -> None:
        """刷新公司列表。"""
        self._list.clear()
        for c in list_companies():
            item = QListWidgetItem(f"{c['name']} ({c['slug']})")
            item.setData(Qt.UserRole, c["id"])
            self._list.addItem(item)

    def _create_company(self) -> None:
        """创建新公司。"""
        name = self._name_input.text().strip()
        if not name:
            return
        result = create_company(name)
        if result:
            self._name_input.clear()
            self._refresh_list()
            QMessageBox.information(self, "成功", f"公司 '{name}' 已创建")
            self.accept()  # 创建后自动关闭，让主窗口刷新
        else:
            QMessageBox.warning(self, "失败", "创建公司失败，请检查网络连接。")


# ── 许可证对话框 ──────────────────────────────────────────────────────────

class LicenseDialog(QDialog):
    """许可证激活对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("许可证管理")
        self.resize(450, 350)

        layout = QVBoxLayout(self)

        # 状态信息
        self._status_label = QLabel("正在查询许可证状态...")
        self._status_label.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self._status_label)

        # 申请码
        self._req_code_label = QLabel("")
        self._req_code_label.setStyleSheet(
            "background:#F1F5F9; padding:8px; border-radius:4px; "
            "font-family:Consolas; font-size:12px;"
        )
        self._req_code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._req_code_label)

        # 激活码输入
        form = QFormLayout()
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("粘贴作者提供的激活码...")
        self._code_input.setStyleSheet("font-family:Consolas; font-size:12px;")
        form.addRow("激活码:", self._code_input)
        layout.addLayout(form)

        # 激活按钮
        activate_btn = QPushButton("✅ 激活")
        activate_btn.setObjectName("primary")
        activate_btn.clicked.connect(self._do_activate)
        layout.addWidget(activate_btn)

        # 加载状态
        self._load_status()

    def _load_status(self) -> None:
        """加载许可证状态。"""
        status = get_license_status()
        if not status:
            self._status_label.setText("❌ 无法获取许可证状态")
            return

        if status.get("activated"):
            expires = status.get("expires_at", "")[:10]
            self._status_label.setText(
                f"✅ 已激活 · 有效期至 {expires}"
            )
        elif status.get("days_remaining", 0) > 0:
            days = status["days_remaining"]
            self._status_label.setText(
                f"⏳ 试用剩余 {days} 天"
            )
            self._req_code_label.setText(
                f"申请码: {status.get('request_code', 'N/A')}\n"
                f"(点击选中 → Ctrl+C 复制)"
            )
        else:
            self._status_label.setText("⚠️ 试用期已到期")

    def _do_activate(self) -> None:
        """提交激活码。"""
        code = self._code_input.text().strip()
        if not code:
            return
        result = activate_license(code)
        if result and result.get("ok"):
            QMessageBox.information(self, "激活成功", "许可证已激活！")
            self._load_status()
        else:
            msg = result.get("error") if result else "网络错误"
            QMessageBox.warning(self, "激活失败", msg)


# ── 设置对话框 ────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """系统设置对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # Tab 1: 系统
        sys_tab = QWidget()
        sys_layout = QVBoxLayout(sys_tab)

        update_btn = QPushButton("⬆️ 系统更新")
        update_btn.clicked.connect(self._do_update)
        sys_layout.addWidget(update_btn)

        restart_btn = QPushButton("🔄 重启服务")
        restart_btn.clicked.connect(self._do_restart)
        sys_layout.addWidget(restart_btn)

        sys_layout.addStretch()
        tabs.addTab(sys_tab, "系统")

        # Tab 2: 许可证
        lic_tab = QWidget()
        lic_layout = QVBoxLayout(lic_tab)
        lic_btn = QPushButton("🔑 许可证管理")
        lic_btn.clicked.connect(lambda: LicenseDialog(self).exec())
        lic_layout.addWidget(lic_btn)
        lic_layout.addStretch()
        tabs.addTab(lic_tab, "许可证")

        layout.addWidget(tabs)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _do_update(self) -> None:
        """触发系统更新。"""
        reply = QMessageBox.question(
            self, "确认更新", "将下载最新代码并重启服务，是否继续？"
        )
        if reply == QMessageBox.Yes:
            result = system_update()
            if result and result.get("restart_scheduled"):
                QMessageBox.information(
                    self, "更新中", "更新完成，服务正在重启...\n请等待几秒后刷新。"
                )
            elif result and result.get("ok"):
                QMessageBox.information(self, "完成", "更新完成。")
            else:
                QMessageBox.warning(
                    self, "失败",
                    result.get("error") if result else "网络错误"
                )

    def _do_restart(self) -> None:
        """重启服务。"""
        reply = QMessageBox.question(
            self, "确认重启", "确定要重启 Trade 服务吗？"
        )
        if reply == QMessageBox.Yes:
            system_restart()
            QMessageBox.information(
                self, "重启中", "服务正在重启，请等待几秒。"
            )
```

- [ ] **Step 2: 在 app.py 中集成对话框**

```python
# 在 MainWindow 的 _build_sidebar 中：
# 设置 item 点击时，如果是⚙️设置，弹出 SettingsDialog
# (替代原来的 QStackedWidget 切换)
```

- [ ] **Step 3: Commit**

```bash
git add windows-standalone/tradewin/dialogs.py
git commit -m "feat: 对话框集合 — 公司管理/许可证/设置"
```

---

### Task 8: PyInstaller 打包配置

**Files:**
- Create: `windows-standalone/tradewin.spec`
- Create: `windows-standalone/build.bat`

- [ ] **Step 1: 编写 tradewin.spec（PyInstaller 配置）**

```python
# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller spec for TradeWin single-exe build."""

import sys
from pathlib import Path

_block_cipher = None

# 项目根目录（父目录的父目录）
_PROJECT_ROOT = Path(SPECPATH).parent.parent
_TRADEWIN_ROOT = Path(SPECPATH)

a = Analysis(
    # 入口脚本
    [str(_TRADEWIN_ROOT / 'tradewin' / 'main.py')],
    pathex=[
        str(_TRADEWIN_ROOT),
        str(_PROJECT_ROOT),
    ],
    binaries=[],
    datas=[
        # 打包静态资源
        (str(_TRADEWIN_ROOT / 'tradewin' / 'resources' / 'icon.ico'),
         'tradewin/resources'),
        (str(_TRADEWIN_ROOT / 'tradewin' / 'resources' / 'style.qss'),
         'tradewin/resources'),
        # 打包 skills 目录（Hermes Agent 需要）
        (str(_PROJECT_ROOT / 'skills'), 'skills'),
        # 打包 .trade-template
        (str(_PROJECT_ROOT / '.trade-template'), '.trade-template'),
        # 打包 trade 包
        (str(_PROJECT_ROOT / 'trade'), 'trade'),
    ],
    hiddenimports=[
        # PySide6
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        # FastAPI / uvicorn
        'uvicorn.loops.auto', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        # Trade 内部模块
        'trade', 'trade.api', 'trade.api.chat', 'trade.api.cron',
        'trade.api.companies', 'trade.api.customers', 'trade.api.libraries',
        'trade.api.orders', 'trade.api.conversations', 'trade.api.memory',
        'trade.api.onboarding', 'trade.api.license', 'trade.api.deps',
        'trade.api.models',
        'trade.database', 'trade.company', 'trade.company.crud',
        'trade.company.workdir',
        'trade.helpers', 'trade.prompts', 'trade.prompt',
        'trade.skill_router', 'trade.skill_registry',
        'trade.chat_memory', 'trade.memory', 'trade.license',
        'trade.onboarding', 'trade.bootstrap',
        # OSINT
        'trade.osint', 'trade.osint.orchestrator', 'trade.osint.whois',
        'trade.osint.email_verify', 'trade.osint.sanctions',
        'trade.osint.sanctions.loader',
        'trade.osint.tech_stack', 'trade.osint.linkedin_verify',
        'trade.osint.scoring', 'trade.osint.constants',
        # Hermes Agent
        'hermes_cli', 'hermes_cli.config', 'hermes_cli.auth',
        'hermes_cli.env_loader', 'hermes_cli.models',
        'hermes_constants', 'run_agent',
        # Standard library
        'asyncio', 'concurrent.futures', 'email', 'json', 'logging',
        'sqlite3', 'xml', 'csv', 'io', 're', 'hashlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',
        'PIL', 'cryptography',  # 如果不需要加密可排除
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=_block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TradeWin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 不显示控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_TRADEWIN_ROOT / 'tradewin' / 'resources' / 'icon.ico'),
)
```

- [ ] **Step 2: 编写 build.bat（Windows 构建脚本）**

```bat
@echo off
echo ========================================
echo  TradeWin Standalone — Build Script
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

REM 安装依赖
echo [1/3] Installing dependencies...
pip install -r requirements.txt
pip install -e ..

REM 清理旧构建
echo [2/3] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 打包
echo [3/3] Building single .exe...
pyinstaller --clean --noconfirm tradewin.spec

REM 完成
echo.
echo ========================================
echo  Build complete!
echo  Executable: dist\TradeWin.exe
echo ========================================
pause
```

- [ ] **Step 3: Commit**

```bash
git add windows-standalone/tradewin.spec windows-standalone/build.bat
git commit -m "feat: PyInstaller 打包配置 + Windows 构建脚本"
```

---

### Task 9: 最终集成测试 + README

**Files:**
- Create: `windows-standalone/README.md`

- [ ] **Step 1: 编写 README.md**

```markdown
# TradeWin — Windows 独立版

Foreign Trade Assistant 的 Windows 原生桌面应用。

## 系统要求

- Windows 10 (1903+) / Windows 11
- 4 GB RAM 以上
- 无需安装 Python — 单一 .exe 文件，双击运行

## 快速开始

1. 下载 `TradeWin.exe`
2. 双击运行
3. 首次启动自动进入 30 天试用期
4. 在设置 → 许可证中输入激活码

## 功能

- 💬 AI 聊天 — 外贸销售助手，支持文档分析、报价生成、客户背调
- 👥 客户管理 — 多公司隔离，客户 CRUD
- 📁 文档库 — 报价单、合同、产品规格等文件分析
- 📋 任务面板 — Cron 定时任务自动化
- 🔑 许可证管理 — 试用/激活
- ⬆️ 一键更新 — git pull + pip install 自动更新

## 开发者构建

在 Windows 上：

```cmd
cd windows-standalone
build.bat
```

构建产物在 `dist/TradeWin.exe`（约 80-120 MB）。

## 技术栈

- **GUI:** PySide6 (Qt6)
- **后端:** FastAPI + uvicorn (daemon thread)
- **AI:** Hermes Agent (NousResearch)
- **打包:** PyInstaller --onefile --windowed
```

- [ ] **Step 2: Commit**

```bash
git add windows-standalone/README.md
git commit -m "docs: TradeWin README — 系统要求/功能/构建说明"
```

---

## 验证清单

- [ ] `python -m tradewin.main` 在 Windows 上可启动
- [ ] 聊天 SSE 流式正常显示
- [ ] 公司/客户 CRUD 正常工作
- [ ] 许可证激活流程正常
- [ ] 系统托盘最小化/恢复正常
- [ ] 一键更新触发重启正常
- [ ] `build.bat` 生成的 TradeWin.exe 可独立运行（不需要 Python）
- [ ] 杀毒软件不误报（PyInstaller 常见问题，需数字签名解决）

## 已知限制

1. **Markdown 渲染**: QTextBrowser 仅支持 HTML 子集，复杂表格/代码块显示有限。可通过嵌入 QWebEngineView 用 marked.js 解决（需额外 ~60MB）
2. **文件大小**: PyInstaller --onefile 打包后约 100MB+（含 Qt6 + Python 标准库）
3. **无自动更新**: exe 本身通过 git pull 自动更新代码，但 PyInstaller 打包的二进制（Qt/Python）不变
4. **杀毒误报**: 无数字签名的 PyInstaller exe 可能被 Windows Defender 误报
