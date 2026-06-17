"""
TradeWin — 聊天视图。

QTextBrowser Markdown 消息列表 + QLineEdit 输入框 + QThread SSE 流式接收。
"""

import json
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QLineEdit, QPushButton, QScrollBar,
)
from PySide6.QtGui import QFont, QTextCursor

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
        self._response_buffer = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._msg_browser = QTextBrowser()
        self._msg_browser.setOpenExternalLinks(True)
        self._msg_browser.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self._msg_browser, 1)

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

    def _send_message(self) -> None:
        query = self._input_field.text().strip()
        if not query:
            return
        self._append_message("🧑 您", query)
        self._input_field.clear()
        self._input_field.setEnabled(False)
        self._response_buffer = ""
        self._msg_browser.moveCursor(QTextCursor.End)
        self._msg_browser.insertHtml(
            '<div style="margin:8px 0; padding:10px 14px; '
            'background:#F0FDF4; border-radius:8px;">'
            '<b style="color:#166534;">🤖 Trade AI</b><br>'
            '<span id="ai-response">⏳ 思考中...</span></div>'
        )
        self._scroll_to_bottom()
        self._worker = ChatStreamWorker(query)
        self._worker.event_received.connect(self._on_sse_event)
        self._worker.finished.connect(self._on_stream_done)
        self._worker.start()

    def _on_sse_event(self, etype: str, data_str: str) -> None:
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return
        if etype == "response":
            chunk = data.get("content", "")
            self._response_buffer += chunk
            html = self._msg_browser.toHtml()
            text = self._response_buffer.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            html = html.replace('<span id="ai-response">⏳ 思考中...</span>', f'<span id="ai-response">{text}</span>')
            self._msg_browser.setHtml(html)
            self._scroll_to_bottom()
        elif etype == "tool_start":
            self._append_status(f"🔧 调用工具: {data.get('tool', 'unknown')}")
        elif etype == "tool_complete":
            self._append_status(f"✅ 工具完成: {data.get('tool', 'unknown')}")
        elif etype == "thinking":
            self._append_status(f"💭 {data.get('content', '思考中...')}")
        elif etype == "error":
            self._append_status(f"❌ {data.get('message', '未知错误')}")

    def _on_stream_done(self) -> None:
        self._input_field.setEnabled(True)
        self._input_field.setFocus()

    def _append_message(self, sender: str, content: str) -> None:
        self._msg_browser.moveCursor(QTextCursor.End)
        bg = "#EFF6FF" if "您" in sender else "#F0FDF4"
        color = "#1E40AF" if "您" in sender else "#166534"
        text = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._msg_browser.insertHtml(
            f'<div style="margin:8px 0; padding:10px 14px; '
            f'background:{bg}; border-radius:8px;">'
            f'<b style="color:{color};">{sender}</b><br>{text}</div>'
        )
        self._scroll_to_bottom()

    def _append_status(self, msg: str) -> None:
        self._msg_browser.moveCursor(QTextCursor.End)
        self._msg_browser.insertHtml(
            f'<div style="margin:4px 0; color:#64748B; font-size:12px;">{msg}</div>'
        )
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        sb = self._msg_browser.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
