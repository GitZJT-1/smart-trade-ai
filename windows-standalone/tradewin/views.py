"""
TradeWin — 嵌入式功能视图。

每个视图是一个 QWidget，直接挂载到主窗口 QStackedWidget，替换原来的 QLabel 占位。
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tradewin.api import (
    delete_customer,
    get_conversation_detail,
    get_cron_jobs,
    get_cron_today,
    get_customer_detail,
    get_library_files,
    get_models_providers,
    list_conversations,
    list_customers,
    list_libraries,
    update_customer,
)

# ═══════════════════════════════════════════════════════════════════════════════
# CustomerView — 客户管理（列表 + 详情 + 编辑 + 删除）
# ═══════════════════════════════════════════════════════════════════════════════

class CustomerView(QWidget):
    """客户管理：左侧可搜索列表，右侧详情表单可编辑保存。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧：客户列表 + 搜索 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 4, 8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索客户名称或国家...")
        self._search.textChanged.connect(self._on_search)
        left_layout.addWidget(self._search)

        self._list = QTreeWidget()
        self._list.setHeaderLabels(["客户名称", "等级", "国家"])
        self._list.setRootIsDecorated(False)
        self._list.setAlternatingRowColors(True)
        self._list.itemClicked.connect(self._on_select)
        left_layout.addWidget(self._list)

        splitter.addWidget(left)

        # ── 右侧：详情编辑 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 8, 8, 8)

        self._form = QFormLayout()
        self._fields = {}
        for key, label in [
            ("name", "客户名称"), ("contact", "联系方式"), ("email", "邮箱"),
            ("phone", "电话"), ("whatsapp", "WhatsApp"), ("wechat", "微信"),
            ("country", "国家"), ("tier", "等级 (A/B/C)"),
            ("linkedin_url", "LinkedIn"), ("company_website", "公司网站"),
            ("note", "备注"),
        ]:
            w = QLineEdit()
            w.setReadOnly(True)
            self._fields[key] = w
            self._form.addRow(label, w)
        right_layout.addLayout(self._form)

        btn_layout = QHBoxLayout()
        self._edit_btn = QPushButton("✏️ 编辑")
        self._edit_btn.clicked.connect(self._toggle_edit)
        btn_layout.addWidget(self._edit_btn)

        self._save_btn = QPushButton("💾 保存")
        self._save_btn.setObjectName("primary")
        self._save_btn.clicked.connect(self._do_save)
        self._save_btn.setVisible(False)
        btn_layout.addWidget(self._save_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self._do_cancel)
        self._cancel_btn.setVisible(False)
        btn_layout.addWidget(self._cancel_btn)

        self._delete_btn = QPushButton("🗑 删除")
        self._delete_btn.setStyleSheet("color: #DC2626;")
        self._delete_btn.clicked.connect(self._do_delete)
        btn_layout.addWidget(self._delete_btn)
        btn_layout.addStretch()

        right_layout.addLayout(btn_layout)
        splitter.addWidget(right)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)
        self._all_customers: list[dict] = []
        self._current_cid: int | None = None
        self._editing = False
        self._refresh()

    def _refresh(self) -> None:
        self._all_customers = list_customers()
        self._populate_list(self._all_customers)

    def _populate_list(self, customers: list[dict]) -> None:
        self._list.clear()
        for c in customers:
            item = QTreeWidgetItem([
                c.get("name", ""),
                c.get("tier", ""),
                c.get("country", ""),
            ])
            item.setData(0, Qt.UserRole, c.get("id"))
            self._list.addTopLevelItem(item)
        for i in range(3):
            self._list.resizeColumnToContents(i)

    def _on_search(self, text: str) -> None:
        if not text.strip():
            self._populate_list(self._all_customers)
            return
        q = text.lower()
        filtered = [
            c for c in self._all_customers
            if q in (c.get("name") or "").lower()
            or q in (c.get("country") or "").lower()
        ]
        self._populate_list(filtered)

    def _on_select(self, item: QTreeWidgetItem) -> None:
        cid = item.data(0, Qt.UserRole)
        if cid is None:
            return
        self._current_cid = cid
        detail = get_customer_detail(cid)
        if not detail:
            return
        for key, w in self._fields.items():
            w.setText(str(detail.get(key, "") or ""))
        self._editing = False
        self._set_readonly(True)

    def _toggle_edit(self) -> None:
        if self._current_cid is None:
            return
        self._editing = True
        self._set_readonly(False)
        self._edit_btn.setVisible(False)
        self._save_btn.setVisible(True)
        self._cancel_btn.setVisible(True)

    def _do_save(self) -> None:
        if self._current_cid is None:
            return
        data = {key: w.text().strip() for key, w in self._fields.items()}
        result = update_customer(self._current_cid, data)
        if result:
            self._editing = False
            self._set_readonly(True)
            self._edit_btn.setVisible(True)
            self._save_btn.setVisible(False)
            self._cancel_btn.setVisible(False)
            self._refresh()
        else:
            QMessageBox.warning(self, "保存失败", "更新客户信息失败，请检查网络连接。")

    def _do_cancel(self) -> None:
        self._editing = False
        self._set_readonly(True)
        self._edit_btn.setVisible(True)
        self._save_btn.setVisible(False)
        self._cancel_btn.setVisible(False)
        # 恢复原值
        self._on_select(self._list.currentItem() or self._list.topLevelItem(0))

    def _do_delete(self) -> None:
        if self._current_cid is None:
            return
        name = self._fields["name"].text()
        r = QMessageBox.question(
            self, "确认删除", f"确定要删除客户「{name}」吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        result = delete_customer(self._current_cid)
        if result:
            self._clear_detail()
            self._current_cid = None
            self._refresh()
        else:
            QMessageBox.warning(self, "删除失败", "删除客户失败，请检查网络连接。")

    def _clear_detail(self) -> None:
        for w in self._fields.values():
            w.setText("")

    def _set_readonly(self, ro: bool) -> None:
        for w in self._fields.values():
            w.setReadOnly(ro)


# ═══════════════════════════════════════════════════════════════════════════════
# LibraryView — 文档库管理（库列表 + 文件浏览）
# ═══════════════════════════════════════════════════════════════════════════════

class LibraryView(QWidget):
    """文档库：左侧库列表，右侧文件浏览器。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧：库列表 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 4, 8)
        left_layout.addWidget(QLabel("文档库列表:"))

        self._lib_tree = QTreeWidget()
        self._lib_tree.setHeaderLabels(["库名称", "根目录"])
        self._lib_tree.setRootIsDecorated(False)
        self._lib_tree.setAlternatingRowColors(True)
        self._lib_tree.itemClicked.connect(self._on_lib_select)
        left_layout.addWidget(self._lib_tree)

        splitter.addWidget(left)

        # ── 右侧：文件列表 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 8, 8, 8)
        right_layout.addWidget(QLabel("文件列表:"))

        self._path_label = QLabel("")
        self._path_label.setStyleSheet("color: #64748B; font-size: 11px;")
        right_layout.addWidget(self._path_label)

        self._file_tree = QTreeWidget()
        self._file_tree.setHeaderLabels(["文件名", "大小", "修改时间"])
        self._file_tree.setRootIsDecorated(True)
        self._file_tree.setAlternatingRowColors(True)
        right_layout.addWidget(self._file_tree)

        splitter.addWidget(right)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)
        self._current_lid: int | None = None
        self._refresh_libs()

    def _refresh_libs(self) -> None:
        self._lib_tree.clear()
        self._file_tree.clear()
        libs = list_libraries()
        if not libs:
            placeholder = QTreeWidgetItem(["（暂无文档库）", ""])
            placeholder.setFlags(Qt.NoItemFlags)
            self._lib_tree.addTopLevelItem(placeholder)
            return
        for lib in libs:
            item = QTreeWidgetItem([
                lib.get("name", ""),
                lib.get("root_path", ""),
            ])
            item.setData(0, Qt.UserRole, lib.get("id"))
            self._lib_tree.addTopLevelItem(item)
        for i in range(2):
            self._lib_tree.resizeColumnToContents(i)

    def _on_lib_select(self, item: QTreeWidgetItem) -> None:
        lid = item.data(0, Qt.UserRole)
        if lid is None:
            return
        self._current_lid = lid
        self._path_label.setText("📂 /")
        self._browse_files(lid, "")

    def _browse_files(self, lid: int, subpath: str) -> None:
        self._file_tree.clear()
        result = get_library_files(lid, subpath)
        if not result:
            return
        files: list[dict] = result.get("files", [])
        if not files:
            placeholder = QTreeWidgetItem(["（空目录）", "", ""])
            placeholder.setFlags(Qt.NoItemFlags)
            self._file_tree.addTopLevelItem(placeholder)
            return
        for f in files:
            name = f.get("name", "")
            is_dir = f.get("is_dir", False) or name.endswith("/")
            size = f.get("size", "")
            mtime = f.get("modified_at", "") or ""
            item = QTreeWidgetItem([
                name.rstrip("/"),
                str(size) if not is_dir else "",
                str(mtime)[:19] if mtime else "",
            ])
            if is_dir:
                item.setData(0, Qt.UserRole, f.get("path", name))
            self._file_tree.addTopLevelItem(item)
        for i in range(3):
            self._file_tree.resizeColumnToContents(i)


# ═══════════════════════════════════════════════════════════════════════════════
# TasksView — 任务面板（cron 任务 + 今日计划 + 执行历史）
# ═══════════════════════════════════════════════════════════════════════════════

class TasksView(QWidget):
    """任务面板：cron 任务定义 + 今日任务 + 最近执行历史。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── 今日任务 ──
        today_gb = QGroupBox("📅 今日任务")
        today_layout = QVBoxLayout(today_gb)
        self._today_table = QTableWidget()
        self._today_table.setColumnCount(3)
        self._today_table.setHorizontalHeaderLabels(["时间", "任务名", "状态"])
        self._today_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._today_table.setAlternatingRowColors(True)
        today_layout.addWidget(self._today_table)
        layout.addWidget(today_gb)

        # ── cron 任务定义 ──
        cron_gb = QGroupBox("⚙️ Cron 任务定义")
        cron_layout = QVBoxLayout(cron_gb)
        self._cron_table = QTableWidget()
        self._cron_table.setColumnCount(4)
        self._cron_table.setHorizontalHeaderLabels(["任务名称", "Skill", "Cron 表达式", "状态"])
        self._cron_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._cron_table.setAlternatingRowColors(True)
        cron_layout.addWidget(self._cron_table)
        layout.addWidget(cron_gb)

        self._refresh()

    def _refresh(self) -> None:
        self._load_cron_jobs()
        self._load_today()

    def _load_cron_jobs(self) -> None:
        jobs = get_cron_jobs()
        self._cron_table.setRowCount(len(jobs))
        for i, j in enumerate(jobs):
            self._cron_table.setItem(i, 0, QTableWidgetItem(str(j.get("name", ""))))
            self._cron_table.setItem(i, 1, QTableWidgetItem(str(j.get("skills", ""))))
            self._cron_table.setItem(i, 2, QTableWidgetItem(str(j.get("schedule", ""))))
            status = "✅ 活跃" if j.get("enabled") else "⏸ 暂停"
            self._cron_table.setItem(i, 3, QTableWidgetItem(status))

    def _load_today(self) -> None:
        today = get_cron_today() or {}
        tasks: list[dict] = today.get("tasks", [])
        history: list[dict] = today.get("recent_runs", [])
        rows: list[dict] = []
        for t in tasks:
            rows.append({
                "time": t.get("scheduled_at", "") or "",
                "name": t.get("name", "") or "",
                "status": "⏳ 待执行",
            })
        for h in history:
            status = "✅ 成功" if h.get("success") else "❌ 失败"
            rows.append({
                "time": str(h.get("executed_at", "") or "")[:19],
                "name": str(h.get("name", "") or ""),
                "status": status,
            })
        self._today_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self._today_table.setItem(i, 0, QTableWidgetItem(r["time"]))
            self._today_table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self._today_table.setItem(i, 2, QTableWidgetItem(r["status"]))


# ═══════════════════════════════════════════════════════════════════════════════
# HistoryView — 对话历史（列表 + 搜索 + 详情）
# ═══════════════════════════════════════════════════════════════════════════════

class HistoryView(QWidget):
    """对话历史：左侧可搜索列表，右侧 Markdown 详情。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧：对话列表 + 搜索 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 4, 8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索对话内容...")
        self._search.textChanged.connect(self._on_search)
        left_layout.addWidget(self._search)

        self._conv_list = QListWidget()
        self._conv_list.itemClicked.connect(self._on_select)
        left_layout.addWidget(self._conv_list)

        splitter.addWidget(left)

        # ── 右侧：对话详情 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 8, 8, 8)

        self._detail = QTextBrowser()
        self._detail.setOpenExternalLinks(True)
        self._detail.setFont(QFont("Microsoft YaHei", 11))
        right_layout.addWidget(self._detail)

        splitter.addWidget(right)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)
        self._all_convs: list[dict] = []
        self._refresh()

    def _refresh(self) -> None:
        self._all_convs = list_conversations(limit=100)
        self._populate(self._all_convs)

    def _populate(self, convs: list[dict]) -> None:
        self._conv_list.clear()
        for c in convs:
            text = (c.get("query") or "")[:80]
            time_str = str(c.get("created_at", "") or "")[:16]
            label = f"[{time_str}] {text}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, c.get("id"))
            self._conv_list.addItem(item)

    def _on_search(self, text: str) -> None:
        if not text.strip():
            self._populate(self._all_convs)
            return
        q = text.lower()
        filtered = [
            c for c in self._all_convs
            if q in (c.get("query") or "").lower()
            or q in (c.get("response") or "").lower()
        ]
        self._populate(filtered)

    def _on_select(self, item: QListWidgetItem) -> None:
        cid = item.data(Qt.UserRole)
        if cid is None:
            return
        detail = get_conversation_detail(cid)
        if not detail:
            self._detail.setPlainText("❌ 无法加载对话详情")
            return
        query = detail.get("query", "")
        response = detail.get("response", "")
        created = str(detail.get("created_at", "") or "")[:19]
        html = (
            f'<div style="margin:8px 0; padding:10px 14px; background:#F1F5F9; '
            f'border-radius:8px;">'
            f'<b style="color:#1E293B;">🧑 用户</b> '
            f'<span style="color:#94A3B8; font-size:11px;">{created}</span><br>'
            f'<pre style="white-space:pre-wrap; font-family:inherit; '
            f'margin:8px 0 0 0;">{query}</pre></div>'
            f'<div style="margin:8px 0; padding:10px 14px; background:#F0FDF4; '
            f'border-radius:8px;">'
            f'<b style="color:#166534;">🤖 Trade AI</b><br>'
            f'<pre style="white-space:pre-wrap; font-family:inherit; '
            f'margin:8px 0 0 0;">{response}</pre></div>'
        )
        self._detail.setHtml(html)


# ═══════════════════════════════════════════════════════════════════════════════
# SettingsView — 设置（LLM / License / 版本更新）
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsView(QWidget):
    """设置面板：许可证状态、LLM 提供商、版本更新。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 许可证 ──
        lic_gb = QGroupBox("🔑 许可证")
        lic_layout = QFormLayout(lic_gb)
        self._lic_status = QLabel("查询中...")
        lic_layout.addRow("状态:", self._lic_status)
        self._req_code_label = QLabel("")
        self._req_code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._req_code_label.setStyleSheet(
            "background:#F1F5F9; padding:6px; border-radius:4px; font-family:Consolas;"
        )
        lic_layout.addRow("申请码:", self._req_code_label)
        code_layout = QHBoxLayout()
        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("粘贴激活码...")
        code_layout.addWidget(self._code_input)
        activate_btn = QPushButton("✅ 激活")
        activate_btn.setObjectName("primary")
        activate_btn.clicked.connect(self._do_activate)
        code_layout.addWidget(activate_btn)
        lic_layout.addRow("激活码:", code_layout)
        layout.addWidget(lic_gb)
        self._load_license()

        # ── LLM 提供商 ──
        llm_gb = QGroupBox("🤖 LLM 提供商")
        llm_layout = QVBoxLayout(llm_gb)
        self._provider_list = QListWidget()
        self._provider_list.setMaximumHeight(120)
        llm_layout.addWidget(self._provider_list)
        layout.addWidget(llm_gb)
        self._load_providers()

        # ── 系统 ──
        sys_gb = QGroupBox("⚙️ 系统")
        sys_layout = QHBoxLayout(sys_gb)
        from tradewin.api import get_status
        status = get_status()
        ver = status.get("version", "?.?.?") if status else "?.?.?"
        sys_layout.addWidget(QLabel(f"当前版本: v{ver}"))
        sys_layout.addStretch()
        update_btn = QPushButton("🔄 检查更新并升级")
        update_btn.clicked.connect(lambda: self._do_update())
        sys_layout.addWidget(update_btn)
        restart_btn = QPushButton("🔁 重启服务")
        restart_btn.clicked.connect(lambda: self._do_restart())
        sys_layout.addWidget(restart_btn)
        layout.addWidget(sys_gb)

        layout.addStretch()

    def _load_license(self) -> None:
        from tradewin.api import get_license_status
        status = get_license_status()
        if not status:
            self._lic_status.setText("❌ 无法获取许可证状态")
            return
        if status.get("activated"):
            expires = str(status.get("expires_at", ""))[:10]
            self._lic_status.setText(f"✅ 已激活（到期: {expires}）")
        else:
            days = status.get("trial_days_left", 0)
            self._lic_status.setText(f"⚠️ 试用版（剩余 {days} 天）")
        self._req_code_label.setText(status.get("request_code", ""))

    def _do_activate(self) -> None:
        code = self._code_input.text().strip()
        if not code:
            return
        from tradewin.api import activate_license
        result = activate_license(code)
        if result and result.get("ok"):
            QMessageBox.information(self, "激活成功", "许可证激活成功！")
            self._code_input.clear()
            self._load_license()
        else:
            QMessageBox.warning(self, "激活失败", result.get("error", "未知错误") if result else "网络错误")

    def _load_providers(self) -> None:
        providers = get_models_providers()
        for p in providers:
            name = p.get("name", p.get("id", "?"))
            enabled = "✅" if p.get("configured") else "⚪"
            self._provider_list.addItem(f"{enabled} {name}")

    def _do_update(self) -> None:
        from tradewin.api import system_update
        QMessageBox.information(self, "更新", "正在后台执行更新，完成后将自动重启服务。\n等待约 10 秒后版本号将自动刷新。")
        system_update()
        # 延迟 10s 重新检查版本（等待后端重启完成）
        QTimer.singleShot(10000, self._refresh_version)

    def _do_restart(self) -> None:
        r = QMessageBox.question(self, "确认重启", "确定要重启 Trade 服务吗？",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r == QMessageBox.Yes:
            from tradewin.api import system_restart
            system_restart()
            QMessageBox.information(self, "重启中", "服务正在重启，请等待几秒。")
            QTimer.singleShot(8000, self._refresh_version)

    def _refresh_version(self) -> None:
        """延迟重新检查版本号（更新/重启后调用）。"""
        from tradewin.api import get_status
        status = get_status()
        if status:
            ver = status.get("version", "?.?.?")
            # 更新 SettingsView 内的版本标签
            for i in range(self.layout().count()):
                w = self.layout().itemAt(i).widget()
                if isinstance(w, QGroupBox) and w.title() == "⚙️ 系统":
                    for j in range(w.layout().count()):
                        item = w.layout().itemAt(j)
                        if isinstance(item.widget(), QLabel) and item.widget().text().startswith("当前版本"):
                            item.widget().setText(f"当前版本: v{ver}")
            # 同时刷新主窗口状态栏
            mw = self.window()
            if hasattr(mw, '_check_version'):
                mw._check_version()
