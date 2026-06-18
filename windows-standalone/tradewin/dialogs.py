"""
TradeWin — 模态对话框集合：公司管理、客户管理、许可证激活、系统设置。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tradewin.api import (
    activate_license,
    create_company,
    get_license_status,
    list_companies,
    list_customers,
    list_libraries,
    system_restart,
    system_update,
)


class CompanyDialog(QDialog):
    """公司选择 + 创建对话框。"""

    company_created = Signal()  # 创建公司后发出，供主窗口刷新列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("公司管理")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._refresh_list()
        layout.addWidget(QLabel("现有公司:"))
        layout.addWidget(self._list)
        hl = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("输入新公司名称...")
        hl.addWidget(self._name_input)
        create_btn = QPushButton("创建")
        create_btn.setObjectName("primary")
        create_btn.clicked.connect(self._create_company)
        hl.addWidget(create_btn)
        layout.addLayout(hl)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_list(self) -> None:
        self._list.clear()
        for c in list_companies():
            item = QListWidgetItem(f"{c['name']} ({c['slug']})")
            item.setData(Qt.UserRole, c["id"])
            self._list.addItem(item)

    def _create_company(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            return
        result = create_company(name)
        if result:
            self._name_input.clear()
            self._refresh_list()
            self.company_created.emit()  # 通知主窗口刷新
            QMessageBox.information(self, "成功", f"公司 '{name}' 已创建")
            self.accept()
        else:
            QMessageBox.warning(self, "失败", "创建公司失败，请检查网络连接。")


class CustomerDialog(QDialog):
    """客户管理对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("客户管理")
        self.resize(600, 450)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("客户列表:"))
        self._tree = QTreeWidget()
        # 固定 4 列表头，避免空列表时被改写成单列
        self._tree.setHeaderLabels(["客户名称", "等级", "国家", "最近跟进"])
        self._tree.setAlternatingRowColors(True)
        self._refresh_list()
        layout.addWidget(self._tree)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_list(self) -> None:
        self._tree.clear()
        customers = list_customers()
        if not customers:
            # 用占位行而不是改写表头，保持 4 列结构
            placeholder = QTreeWidgetItem(["（暂无客户数据）", "", "", ""])
            placeholder.setFlags(Qt.NoItemFlags)  # 不可选中
            self._tree.addTopLevelItem(placeholder)
            return
        for c in customers:
            item = QTreeWidgetItem([
                c.get("name", ""),
                c.get("tier", ""),
                c.get("country", ""),
                (c.get("updated_at", "") or "")[:10],
            ])
            item.setData(0, Qt.UserRole, c.get("id"))
            self._tree.addTopLevelItem(item)
        for i in range(4):
            self._tree.resizeColumnToContents(i)


class LibraryDialog(QDialog):
    """文档库管理对话框。

    展示当前公司下的所有文档库（名称 + root_path）。
    TradeWin 暂不提供创建/删除入口（由 AI 在聊天中通过工具完成）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文档库")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("文档库列表:"))
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["库名称", "根目录", "说明"])
        self._tree.setAlternatingRowColors(True)
        self._refresh_list()
        layout.addWidget(self._tree)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_list(self) -> None:
        self._tree.clear()
        libs = list_libraries()
        if not libs:
            placeholder = QTreeWidgetItem(["（暂无文档库）", "", ""])
            placeholder.setFlags(Qt.NoItemFlags)
            self._tree.addTopLevelItem(placeholder)
            return
        for lib in libs:
            item = QTreeWidgetItem([
                lib.get("name", ""),
                lib.get("root_path", ""),
                lib.get("description", "") or "",
            ])
            item.setData(0, Qt.UserRole, lib.get("id"))
            self._tree.addTopLevelItem(item)
        for i in range(3):
            self._tree.resizeColumnToContents(i)


class LicenseDialog(QDialog):
    """许可证激活对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("许可证管理")
        self.resize(450, 350)
        layout = QVBoxLayout(self)
        self._status_label = QLabel("正在查询许可证状态...")
        self._status_label.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self._status_label)
        self._req_code_label = QLabel("")
        self._req_code_label.setStyleSheet(
            "background:#F1F5F9; padding:8px; border-radius:4px; font-family:Consolas; font-size:12px;"
        )
        self._req_code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._req_code_label)
        form = QFormLayout()
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("粘贴作者提供的激活码...")
        self._code_input.setStyleSheet("font-family:Consolas; font-size:12px;")
        form.addRow("激活码:", self._code_input)
        layout.addLayout(form)
        activate_btn = QPushButton("✅ 激活")
        activate_btn.setObjectName("primary")
        activate_btn.clicked.connect(self._do_activate)
        layout.addWidget(activate_btn)
        self._load_status()

    def _load_status(self) -> None:
        status = get_license_status()
        if not status:
            self._status_label.setText("❌ 无法获取许可证状态")
            return
        if status.get("activated"):
            expires = status.get("expires_at", "")[:10]
            self._status_label.setText(f"✅ 已激活 · 有效期至 {expires}")
        elif status.get("days_remaining", 0) > 0:
            days = status["days_remaining"]
            self._status_label.setText(f"⏳ 试用剩余 {days} 天")
            self._req_code_label.setText(
                f"申请码: {status.get('request_code', 'N/A')}\n(点击选中 → Ctrl+C 复制)"
            )
        else:
            self._status_label.setText("⚠️ 试用期已到期")

    def _do_activate(self) -> None:
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


class SettingsDialog(QDialog):
    """系统设置对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

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
        reply = QMessageBox.question(self, "确认更新", "将下载最新代码并重启服务，是否继续？")
        if reply == QMessageBox.Yes:
            result = system_update()
            if result and result.get("restart_scheduled"):
                QMessageBox.information(self, "更新中", "更新完成，服务正在重启...\n请等待几秒后刷新。")
            elif result and result.get("ok"):
                QMessageBox.information(self, "完成", "更新完成。")
            else:
                QMessageBox.warning(self, "失败", result.get("error") if result else "网络错误")

    def _do_restart(self) -> None:
        reply = QMessageBox.question(self, "确认重启", "确定要重启 Trade 服务吗？")
        if reply == QMessageBox.Yes:
            system_restart()
            QMessageBox.information(self, "重启中", "服务正在重启，请等待几秒。")
