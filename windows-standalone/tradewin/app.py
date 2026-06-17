"""
TradeWin — 主窗口。

布局: QSplitter
  ├── 左侧 QTreeWidget（侧边栏导航 + 公司选择器）
  └── 右侧 QStackedWidget（chat/customers/libraries/tasks/settings 视图）
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
from tradewin.chat import ChatView


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
        self._splitter.setSizes([250, 950])

        self._stack = QStackedWidget()
        self._splitter.addWidget(self._stack)

        # 占位视图（后续 Task 替换为实际组件）
        self._chat_view = ChatView()
        self._customers_view = QLabel("👥 客户管理 — 待实现")
        self._customers_view.setAlignment(Qt.AlignCenter)
        self._libraries_view = QLabel("📁 文档库 — 待实现")
        self._libraries_view.setAlignment(Qt.AlignCenter)
        self._tasks_view = QLabel("📋 任务面板 — 待实现")
        self._tasks_view.setAlignment(Qt.AlignCenter)
        self._settings_view = QLabel("⚙️ 设置 — 待 Task 7 实现")
        self._settings_view.setAlignment(Qt.AlignCenter)

        self._stack.addWidget(self._chat_view)       # index 0
        self._stack.addWidget(self._customers_view)   # index 1
        self._stack.addWidget(self._libraries_view)   # index 2
        self._stack.addWidget(self._tasks_view)       # index 3
        self._stack.addWidget(self._settings_view)    # index 4

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
        """构建左侧侧边栏（公司选择器 + 导航树）。"""
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

        chat_item = QTreeWidgetItem(["💬 聊天"])
        chat_item.setData(0, Qt.UserRole, 0)
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
        self._nav_tree.setCurrentItem(chat_item)
        layout.addWidget(self._nav_tree)

        return container

    def _on_nav_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        """导航树点击：切换到对应的 stacked widget 页面。"""
        idx = item.data(0, Qt.UserRole)
        if idx is not None:
            self._stack.setCurrentIndex(idx)

    def _on_company_changed(self, index: int) -> None:
        """公司选择变更：通知 API 客户端。"""
        cid = self._company_combo.itemData(index)
        if cid:
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
        """检查版本状态并在状态栏显示。"""
        status = get_status()
        if status:
            self._version_label.setText(f"v{status.get('version', '?.?.?')}")
            latest = status.get("latest_version")
            if latest and status.get("version") != latest:
                self._status_bar.showMessage(f"新版本 {latest} 可用！")

    def get_stack(self) -> QStackedWidget:
        return self._stack

    def refresh_companies(self) -> None:
        """刷新公司列表（例如公司创建后调用）。"""
        self._load_companies()
