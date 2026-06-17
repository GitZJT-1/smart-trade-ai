"""
TradeWin — 系统托盘图标。

功能：托盘图标、右键菜单（显示/退出）、双击恢复窗口、Windows 通知气泡。
"""

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class TrayManager:
    """系统托盘管理器。"""

    def __init__(self, app: QApplication, main_window):
        self._app = app
        self._main_window = main_window
        icon_path = Path(__file__).parent / "resources" / "icon.ico"
        icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip("TradeWin — 外贸智能助手")
        menu = QMenu()
        show_action = QAction("📋 显示主窗口")
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("❌ 退出")
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _show_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _quit(self) -> None:
        self._app.quit()

    def show_notification(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)
