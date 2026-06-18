"""
TradeWin — 聊天视图。

QTextBrowser Markdown 消息列表 + QLineEdit 输入框 + QThread SSE 流式接收。
每条 AI 回复附「📋 复制」按钮，一键将内容写入剪贴板。
"""

import json

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from tradewin.api import stream_chat


class ChatStreamWorker(QThread):
    """后台线程执行 SSE 流式聊天，通过 signal 投递事件到主线程。"""

    event_received = Signal(str, str)  # (event_type, json_data)

    def __init__(self, query: str, library_id: int | None = None):
        super().__init__()
        self._query = query
        self._library_id = library_id

    def run(self) -> None:
        def _on_event(etype: str, data: dict) -> None:
            self.event_received.emit(etype, json.dumps(data, ensure_ascii=False))
        stream_chat(self._query, _on_event, library_id=self._library_id)


class ChatView(QWidget):
    """TradeWin 聊天主界面。"""

    def __init__(self):
        super().__init__()
        self._response_buffer = ""  # 当前 SSE 流累积的纯文本回复
        self._msg_counter = 0       # 消息序号，用于为每条 AI 回复生成唯一 anchor
        self._chat_context = ""     # 当前聊天上下文（daily/lead/platform/social/customs/osint）

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── 上下文指示条 ─────────────────────────────────────────────────
        self._context_label = QLabel("")
        self._context_label.setStyleSheet(
            "background: #EFF6FF; color: #1E40AF; padding: 4px 12px; "
            "font-size: 12px; border-bottom: 1px solid #BFDBFE;"
        )
        self._context_label.setVisible(False)
        layout.addWidget(self._context_label)

        # ── 消息显示区 ──────────────────────────────────────────────────
        self._msg_browser = QTextBrowser()
        self._msg_browser.setOpenExternalLinks(True)
        self._msg_browser.setFont(QFont("Microsoft YaHei", 11))
        # 捕获 anchor 点击事件，处理「📋 复制」链接
        self._msg_browser.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self._msg_browser, 1)

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
        # 用户消息（不需要复制按钮）
        self._append_message("🧑 您", query, copyable=False)
        self._input_field.clear()
        self._input_field.setEnabled(False)

        # AI 消息占位：先插入头部（含复制按钮），再记录 anchor cursor
        # 后续 SSE 增量更新通过 anchor cursor 定位，无需 toHtml()/setHtml()
        self._msg_counter += 1
        self._copy_id = f"ai-response-{self._msg_counter}"
        self._response_buffer = ""

        self._msg_browser.moveCursor(QTextCursor.End)
        self._msg_browser.insertHtml(
            '<div style="margin:8px 0; padding:10px 14px; '
            'background:#F0FDF4; border-radius:8px;">'
            '<div style="display:flex; justify-content:space-between; align-items:center;">'
            '<b style="color:#166534;">🤖 Trade AI</b>'
            f'<a href="copy://{self._copy_id}" '
            'style="color:#9CA3AF; font-size:11px; text-decoration:none; '
            'padding:2px 6px; border:1px solid #D1D5DB; border-radius:4px;">📋 复制</a>'
            '</div><br>'
        )
        # 保存 anchor cursor：当前位置即为 AI 回复文本的起始点
        self._ai_anchor_cursor = QTextCursor(self._msg_browser.textCursor())
        # 插入占位文本（后续 _update_ai_message 会替换它）
        self._msg_browser.insertText("⏳ 思考中...")
        self._scroll_to_bottom()

        # 启动 SSE 后台线程
        self._worker = ChatStreamWorker(query)
        self._worker.event_received.connect(self._on_sse_event)
        self._worker.finished.connect(self._on_stream_done)
        self._worker.start()

    # ── SSE 事件处理 ──────────────────────────────────────────────────────

    # ── 聊天上下文 ──────────────────────────────────────────────────────────

    def set_chat_context(self, ctx: str) -> None:
        """设置聊天上下文（从侧边栏子导航调用）。

        不同上下文在输入框显示不同的 placeholder 提示。
        """
        hints = {
            "daily": "输入'今日简报'或具体问题...",
            "lead": "描述产品和目标市场，我帮你找客户 / 写开发信...",
            "platform": "粘贴阿里国际站链接，或描述平台诊断需求...",
            "social": "告诉我平台和目标受众，我帮你制定社媒计划...",
            "customs": "输入产品 HS 编码或产品名 + 目标市场...",
            "osint": "输入公司名 / 域名 / 邮箱，我帮你做背景调查...",
        }
        self._chat_context = ctx
        hint = hints.get(ctx, "")
        self._input_field.setPlaceholderText(hint)
        labels = {
            "daily": "📰 每日简报",
            "lead": "🎯 客户开发",
            "platform": "🏪 平台诊断",
            "social": "📱 社媒营销",
            "customs": "📊 海关数据",
            "osint": "🔍 客户背调",
        }
        label = labels.get(ctx, "")
        if label:
            self._context_label.setText(f"当前模式: {label}")
            self._context_label.setVisible(True)
        else:
            self._context_label.setVisible(False)

    def _on_sse_event(self, etype: str, data_str: str) -> None:
        """处理 SSE 事件（在主线程中执行）。"""
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return
        if etype == "response":
            chunk = data.get("content", "")
            self._response_buffer += chunk
            # 增量更新：用 QTextCursor 定位到 AI 回复 anchor，仅重写该段文本
            # 避免 toHtml()/setHtml() 整文档重排造成的 O(n²) 性能问题
            self._update_ai_message(self._response_buffer)
        elif etype == "tool_start":
            self._append_status(f"🔧 调用工具: {data.get('tool', 'unknown')}")
        elif etype == "tool_complete":
            self._append_status(f"✅ 工具完成: {data.get('tool', 'unknown')}")
        elif etype == "thinking":
            self._append_status(f"💭 {data.get('content', '思考中...')}")
        elif etype == "error":
            self._append_status(f"❌ {data.get('message', '未知错误')}")

    def _update_ai_message(self, full_text: str) -> None:
        """增量更新当前 AI 回复的内容。

        通过保存的 anchor QTextCursor 定位到 AI 回复占位文本的起始位置，
        删除旧内容并插入新内容。相比 toHtml()/setHtml() 全文重排，
        此方式只触发局部重排，长回答下从 O(n²) 降到 O(n)。

        Args:
            full_text: 当前累积的完整回复文本（纯文本，含换行）
        """
        cursor = self._msg_browser.textCursor()
        # 切换到 AI 回复 anchor 位置（_send_message 中保存）
        anchor_cursor = getattr(self, '_ai_anchor_cursor', None)
        if anchor_cursor is not None:
            # 复制 anchor cursor 以免修改原对象
            cursor = QTextCursor(anchor_cursor)
        # 选中从 anchor 到末尾的范围（即旧 AI 文本），用新文本替换
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        # 插入新文本（QTextCursor.insertText 会自动处理 HTML 转义）
        # 先删除选中内容，再插入
        cursor.removeSelectedText()
        # 保留换行：QTextCursor.insertText 不会解释 HTML，但会保留 \\n 为段落分隔
        # 使用 insertText 配配 plain text，让 Qt 自动处理换行渲染
        cursor.insertText(full_text if full_text else "⏳ 思考中...")
        self._scroll_to_bottom()

    def _on_stream_done(self) -> None:
        """SSE 流结束 → 恢复输入框 + 替换复制链接的 copy_id 指向纯文本。"""
        self._input_field.setEnabled(True)
        self._input_field.setFocus()
        # 将 copy_id 存入内部寄存器，供 _on_anchor_clicked 查找
        if not hasattr(self, '_copy_texts'):
            self._copy_texts = {}
        self._copy_texts[self._copy_id] = self._response_buffer

    # ── 复制到剪贴板 ──────────────────────────────────────────────────────

    def _on_anchor_clicked(self, url) -> None:
        """处理 QTextBrowser 中的链接点击。

        普通链接（http/https）由 QTextBrowser.setOpenExternalLinks(True) 自动打开。
        copy:// 协议的链接由本方法处理，将对应消息文本写入系统剪贴板。
        """
        url_str = url.toString()
        if url_str.startswith("copy://"):
            copy_id = url_str[7:]  # 去掉 "copy://" 前缀
            text = ""
            if hasattr(self, '_copy_texts'):
                text = self._copy_texts.get(copy_id, "")
            if not text:
                # SSE 完成前点击了复制 → 取当前 _response_buffer
                text = getattr(self, '_response_buffer', "")
            if text:
                QApplication.clipboard().setText(text)
            else:
                QApplication.clipboard().setText("（暂无内容）")

    # ── UI 辅助 ───────────────────────────────────────────────────────────

    def _append_message(self, sender: str, content: str, copyable: bool = False) -> None:
        """追加一条完整消息到消息浏览器。

        Args:
            sender: 发送者标签（如 "🧑 您" / "🤖 Trade AI"）
            content: 消息文本
            copyable: True 时在消息右侧附加「📋 复制」按钮
        """
        self._msg_browser.moveCursor(QTextCursor.End)
        bg = "#EFF6FF" if "您" in sender else "#F0FDF4"
        color = "#1E40AF" if "您" in sender else "#166534"
        text = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        if copyable:
            self._msg_counter += 1
            cid = f"static-msg-{self._msg_counter}"
            if not hasattr(self, '_copy_texts'):
                self._copy_texts = {}
            self._copy_texts[cid] = content
            self._msg_browser.insertHtml(
                f'<div style="margin:8px 0; padding:10px 14px; '
                f'background:{bg}; border-radius:8px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                f'<b style="color:{color};">{sender}</b>'
                f'<a href="copy://{cid}" '
                'style="color:#9CA3AF; font-size:11px; text-decoration:none; '
                'padding:2px 6px; border:1px solid #D1D5DB; border-radius:4px;">📋 复制</a>'
                f'</div>'
                f'<br>{text}</div>'
            )
        else:
            self._msg_browser.insertHtml(
                f'<div style="margin:8px 0; padding:10px 14px; '
                f'background:{bg}; border-radius:8px;">'
                f'<b style="color:{color};">{sender}</b><br>{text}</div>'
            )
        self._scroll_to_bottom()

    def _append_status(self, msg: str) -> None:
        """追加状态消息（工具调用/思考过程）。"""
        self._msg_browser.moveCursor(QTextCursor.End)
        self._msg_browser.insertHtml(
            f'<div style="margin:4px 0; color:#64748B; font-size:12px;">{msg}</div>'
        )
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """滚动消息浏览器到底部。"""
        sb = self._msg_browser.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
