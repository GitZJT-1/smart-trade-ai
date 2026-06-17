"""
TradeWin — 首次运行向导。

引导用户完成 Hermes 安装 → LLM 配置 → API Key 设置 → Skills 安装 → 数据库初始化。
采用 QWizard 多页表单，每页一个步骤，支持上一步/下一步导航。
"""

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)


class SetupWorker(QThread):
    """后台执行安装步骤（Hermes pip install + skills + database）。"""

    progress = Signal(str)  # 进度消息
    finished_setup = Signal(bool)  # True = 成功

    def __init__(self):
        super().__init__()
        self._steps = []

    def set_steps(self, steps: list[callable]) -> None:
        """设置要执行的安装步骤（每个 step 是 (description, callable) 元组）。"""
        self._callbacks = steps

    def run(self) -> None:
        """顺序执行每个安装步骤。"""

        all_ok = True
        for desc, func in self._callbacks:
            self.progress.emit(f"⏳ {desc}...")
            ok = func(progress_callback=lambda msg: self.progress.emit(msg))
            if not ok:
                self.progress.emit(f"❌ {desc} 失败")
                all_ok = False
                break
            self.progress.emit(f"✅ {desc} 完成")
        self.finished_setup.emit(all_ok)


# ── 向导页 1: 欢迎 ────────────────────────────────────────────────────────

class WelcomePage(QWizardPage):
    """欢迎页 — 介绍 TradeWin 功能。"""

    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用 TradeWin")
        self.setSubTitle("外贸智能助手 — Windows 独立版")

        layout = QVBoxLayout(self)
        intro = QLabel(
            "TradeWin 是一款面向外贸销售团队的 AI 助手，可以帮您：\n\n"
            "• 💬 智能聊天 — 分析报价单、生成开发信、回答外贸问题\n"
            "• 🔍 客户背调 — OFAC 制裁筛查 + 邮箱验证 + 技术栈检测\n"
            "• 📁 文档管理 — 多公司隔离、报价/合同/产品规格分类存储\n"
            "• 📋 定时任务 — 早安简报、邮件跟进、LinkedIn 营销自动化\n\n"
            "接下来将引导您完成首次配置（约 2 分钟）。"
        )
        intro.setWordWrap(True)
        intro.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(intro)


# ── 向导页 2: LLM 提供商选择 ──────────────────────────────────────────────

class ProviderPage(QWizardPage):
    """LLM 提供商选择 — 下拉框 + 模型预览。"""

    def __init__(self):
        super().__init__()
        self.setTitle("选择 AI 引擎")
        self.setSubTitle("TradeWin 需要一个 LLM（大语言模型）来驱动 AI 助手")

        from tradewin.setup import get_available_providers

        layout = QVBoxLayout(self)

        # 提供商下拉框
        layout.addWidget(QLabel("选择 LLM 提供商:"))
        self._provider_combo = QComboBox()
        self._providers = get_available_providers()
        for p in self._providers:
            self._provider_combo.addItem(f"{p['name']} — {p['description']}", p)
        layout.addWidget(self._provider_combo)

        # 模型预览
        self._model_label = QLabel("")
        self._model_label.setStyleSheet(
            "color: #64748B; font-size: 12px; padding: 4px 8px;"
        )
        layout.addWidget(self._model_label)

        # 提示
        hint = QLabel(
            "💡 推荐：DeepSeek V4 Pro（性价比高）或 MiniMax M3（中文外贸场景最优）\n"
            "   如果您已有 OpenAI / Anthropic 的 API Key，也可以选择对应提供商。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748B; font-size: 11px; margin-top: 12px;")
        layout.addWidget(hint)

        self._provider_combo.currentIndexChanged.connect(self._update_model_preview)
        self._update_model_preview(0)

        self.registerField("provider*", self._provider_combo, "currentData",
                          self._provider_combo.currentIndexChanged)

    def _update_model_preview(self, index: int) -> None:
        """更新模型预览文本。"""
        data = self._provider_combo.itemData(index)
        if data:
            models = data.get("models", [])
            self._model_label.setText(
                f"可用模型: {', '.join(models)}"
            )


# ── 向导页 3: API Key 输入 ────────────────────────────────────────────────

class ApiKeyPage(QWizardPage):
    """API Key 输入 — 密码框 + 获取链接 + 测试连接按钮。"""

    def __init__(self):
        super().__init__()
        self.setTitle("配置 API 密钥")
        self.setSubTitle("在 LLM 提供商官网注册并获取 API Key")

        layout = QVBoxLayout(self)

        # API Key 输入
        layout.addWidget(QLabel("API Key:"))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.Password)
        self._key_input.setPlaceholderText("sk-... 或 eyJ...")
        self._key_input.setStyleSheet("font-family: Consolas; font-size: 13px;")
        layout.addWidget(self._key_input)

        # 显示/隐藏 切换
        self._show_cb = QCheckBox("显示密钥")
        self._show_cb.toggled.connect(
            lambda checked: self._key_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        layout.addWidget(self._show_cb)

        # 获取链接
        self._link_label = QLabel("")
        self._link_label.setOpenExternalLinks(True)
        self._link_label.setStyleSheet("color: #3B82F6; font-size: 12px;")
        layout.addWidget(self._link_label)

        # Tavily Key（可选）
        layout.addWidget(QLabel("Tavily Search API Key（可选）:"))
        self._tavily_input = QLineEdit()
        self._tavily_input.setEchoMode(QLineEdit.Password)
        self._tavily_input.setPlaceholderText("tvly-... （用于联网搜索，可选）")
        self._tavily_input.setStyleSheet("font-family: Consolas; font-size: 13px;")
        layout.addWidget(self._tavily_input)

        hint = QLabel(
            "💡 Tavily 提供每月 1000 次免费搜索额度，注册地址: https://tavily.com"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748B; font-size: 11px; margin-top: 8px;")
        layout.addWidget(hint)

        self.registerField("api_key*", self._key_input)
        self.registerField("tavily_key", self._tavily_input)

    def initializePage(self) -> None:
        """根据向导页 2 的选择更新获取链接。"""
        provider_data = self.wizard().page(1)._provider_combo.currentData()
        if provider_data:
            key_url = provider_data.get("key_url", "")
            key_name = provider_data.get("key_name", "")
            self._link_label.setText(
                f'📎 获取 {key_name}: <a href="{key_url}">{key_url}</a>'
            )


# ── 向导页 4: 自动安装 ────────────────────────────────────────────────────

class InstallPage(QWizardPage):
    """自动安装 — 进度条 + 日志。"""

    def __init__(self):
        super().__init__()
        self.setTitle("正在安装")
        self.setSubTitle("请稍候，正在自动配置环境...")

        layout = QVBoxLayout(self)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # 不确定进度条（marquee）
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "background: #1E293B; color: #E2E8F0; font-family: Consolas; font-size: 11px;"
        )
        self._log.setMaximumHeight(300)
        layout.addWidget(self._log)

        self._worker = SetupWorker()

    def initializePage(self) -> None:
        """启动后台安装。"""
        provider_data = self.wizard().page(1)._provider_combo.currentData()
        provider_id = provider_data["id"] if provider_data else "openai"
        api_key = self.field("api_key")
        tavily_key = self.field("tavily_key")

        from tradewin.setup import (
            init_trade_database,
            install_hermes,
            install_trade_skills,
            is_hermes_installed,
            write_hermes_config,
            write_hermes_env,
        )

        # 构建安装步骤列表
        steps = []

        if not is_hermes_installed():
            steps.append(("安装 Hermes Agent", lambda cb=None: install_hermes(cb)))

        steps.append(("安装 Trade Skills", lambda cb=None: install_trade_skills(cb)))
        steps.append(("初始化数据库", lambda cb=None: init_trade_database(cb)))

        if api_key:
            steps.append(("写入 API Key 配置", lambda cb=None: (
                write_hermes_env(provider_id, api_key, tavily_key)
                and write_hermes_config(provider_id)
            )))

        self._worker.set_steps(steps)
        self._worker.progress.connect(self._append_log)
        self._worker.finished_setup.connect(self._on_finished)
        self._worker.start()

    def _append_log(self, msg: str) -> None:
        """追加安装日志。"""
        self._log.append(msg)
        # 自动滚动到底部
        sb = self._log.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_finished(self, success: bool) -> None:
        """安装完成回调。"""
        self._progress.setRange(0, 100)
        if success:
            self._progress.setValue(100)
            self._append_log("\n✅ 环境配置完成！点击「完成」启动 TradeWin。")
            self.wizard().button(QWizard.FinishButton).setEnabled(True)
        else:
            self._append_log("\n❌ 部分步骤失败，请检查日志后重试。")
            self.wizard().button(QWizard.BackButton).setEnabled(True)


# ── 主向导 ────────────────────────────────────────────────────────────────

class FirstRunWizard(QWizard):
    """首次运行向导 — 4 页表单式流程。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TradeWin — 首次配置向导")
        self.resize(600, 500)
        self.setWizardStyle(QWizard.ModernStyle)

        self._welcome = WelcomePage()
        self._provider = ProviderPage()
        self._api_key = ApiKeyPage()
        self._install = InstallPage()

        self.addPage(self._welcome)
        self.addPage(self._provider)
        self.addPage(self._api_key)
        self.addPage(self._install)

        self.setButtonText(QWizard.NextButton, "下一步 →")
        self.setButtonText(QWizard.BackButton, "← 上一步")
        self.setButtonText(QWizard.FinishButton, "✅ 完成")

    def get_config(self) -> dict:
        """返回用户选择的配置。"""
        provider_data = self._provider._provider_combo.currentData()
        return {
            "provider": provider_data["id"] if provider_data else "openai",
            "api_key": self.field("api_key"),
            "tavily_key": self.field("tavily_key"),
        }
