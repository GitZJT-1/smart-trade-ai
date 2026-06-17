"""
TradeWin — Qt 主题系统。

定义亮色/暗色两套调色板，通过 Fusion style + QSS 实现现代化 Windows 原生外观。
颜色常量与现有 trade_chat.html CSS 变量对齐。
"""

from PySide6.QtGui import QColor, QPalette
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
