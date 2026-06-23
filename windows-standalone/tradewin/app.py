"""
TradeWin — 主窗口。

布局: QSplitter
  ├── 左侧 QTreeWidget（侧边栏导航 + 公司选择器）
  └── 右侧 QStackedWidget（chat/customers/libraries/tasks/history/settings 视图）
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tradewin.api import get_status, init_session, list_companies, set_company, switch_company
from tradewin.chat import ChatView
from tradewin.themes import PRIMARY_DARK
from tradewin.views import CustomerView, HistoryView, LibraryView, SettingsView, TasksView

# 聊天子导航：选中后设置 ChatView 的上下文
_CHAT_CONTEXTS = [
    ("每日简报", "daily"),
    ("客户开发", "lead"),
    ("平台诊断", "platform"),
    ("社媒营销", "social"),
    ("海关数据", "customs"),
    ("客户背调", "osint"),
]


class MainWindow(QMainWindow):
    """TradeWin 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TradeWin — 外贸智能助手")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self._init_session()

        self._splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self._splitter)

        self._sidebar = self._build_sidebar()
        self._splitter.addWidget(self._sidebar)
        self._splitter.setSizes([175, 1025])

        self._stack = QStackedWidget()
        self._splitter.addWidget(self._stack)

        # 实际视图（替换原来的 QLabel 占位）
        self._chat_view = ChatView()
        self._customers_view = CustomerView()
        self._libraries_view = LibraryView()
        self._tasks_view = TasksView()
        self._history_view = HistoryView()
        self._settings_view = SettingsView()

        self._stack.addWidget(self._chat_view)       # index 0
        self._stack.addWidget(self._customers_view)   # index 1
        self._stack.addWidget(self._libraries_view)   # index 2
        self._stack.addWidget(self._tasks_view)       # index 3
        self._stack.addWidget(self._history_view)     # index 4
        self._stack.addWidget(self._settings_view)    # index 5

        self._stack.setCurrentIndex(0)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._version_label = QLabel("v?.?.?")
        self._status_bar.addPermanentWidget(self._version_label)

        self._load_companies()
        self._check_version()

    def _init_session(self) -> None:
        """从本地 Trade 服务获取 session token。"""
        result = init_session()
        if result is None:
            QMessageBox.warning(
                self, "连接失败",
                "无法连接到本地 Trade 服务 (127.0.0.1:9119)。\n请确认服务已启动。"
            )

    def _build_sidebar(self) -> QWidget:
        """构建左侧侧边栏（公司选择器 + 导航树，含聊天子导航）。"""
        container = QWidget()
        container.setStyleSheet(f"background: {PRIMARY_DARK.name()}; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._company_combo = QComboBox()
        self._company_combo.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.1); color: #E2E8F0; "
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; "
            "padding: 6px 10px; margin: 8px; }"
            "QComboBox QAbstractItemView { background: #1E293B; color: #E2E8F0; }"
        )
        self._company_combo.currentIndexChanged.connect(self._on_company_changed)
        layout.addWidget(self._company_combo)

        self._nav_tree = QTreeWidget()
        self._nav_tree.setHeaderHidden(True)
        self._nav_tree.setStyleSheet(
            "QTreeWidget { background: transparent; border: none; color: #94A3B8; "
            "font-size: 14px; }"
            "QTreeWidget::item { padding: 8px 12px; }"
            "QTreeWidget::item:selected { background: rgba(59,130,246,0.2); color: #FFFFFF; }"
        )

        # ── 聊天（含子导航）──
        chat_parent = QTreeWidgetItem(["💬 聊天"])
        chat_parent.setData(0, Qt.UserRole, 0)
        chat_parent.setFlags(chat_parent.flags() & ~Qt.ItemIsSelectable)
        self._nav_tree.addTopLevelItem(chat_parent)

        for label, ctx in _CHAT_CONTEXTS:
            child = QTreeWidgetItem([f"  {label}"])
            child.setData(0, Qt.UserRole, (0, ctx))
            chat_parent.addChild(child)

        # ── 功能视图 ──
        nav_items = [
            ("👥 客户管理", 1),
            ("📁 文档库", 2),
            ("📋 任务面板", 3),
            ("📜 对话历史", 4),
            ("⚙️ 设置", 5),
        ]
        for label, idx in nav_items:
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.UserRole, idx)
            self._nav_tree.addTopLevelItem(item)

        self._nav_tree.expandAll()
        self._nav_tree.itemClicked.connect(self._on_nav_clicked)
        layout.addWidget(self._nav_tree)

        return container

    def _on_nav_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        """导航树点击：切换到对应视图，或设置聊天上下文。"""
        data = item.data(0, Qt.UserRole)
        if data is None:
            return

        # 聊天子导航: (0, context_str)
        if isinstance(data, tuple) and data[0] == 0:
            ctx = data[1]
            self._stack.setCurrentIndex(0)
            self._chat_view.set_chat_context(ctx)
            return

        # 普通视图: int index
        idx = int(data)
        self._stack.setCurrentIndex(idx)

    def _on_company_changed(self, index: int) -> None:
        """公司选择变更：先通知后端切换 session 绑定，再更新本地 header。"""
        cid = self._company_combo.itemData(index)
        if cid:
            switch_company(int(cid))
            set_company(str(cid))

    def _load_companies(self) -> None:
        """从 API 加载公司列表，填充选择器下拉框。"""
        companies = list_companies()
        self._company_combo.clear()
        for c in companies:
            self._company_combo.addItem(
                f"{'🟢 ' if c.get('is_active') else '⚫ '}{c['name']}", c["id"]
            )

    def _check_version(self) -> None:
        """检查版本状态并在状态栏显示（仅在 session 存活期调用一次）。"""
        status = get_status()
        if status:
            self._version_label.setText(f"v{status.get('version', '?.?.?')}")
            latest = status.get("latest_version")
            if latest and status.get("version") != latest:
                self._status_bar.showMessage(f"新版本 {latest} 可用！", 15000)
            else:
                self._status_bar.clearMessage()

    def get_stack(self) -> QStackedWidget:
        return self._stack

    def refresh_companies(self) -> None:
        """刷新公司列表（例如公司创建后调用）。"""
        self._load_companies()
