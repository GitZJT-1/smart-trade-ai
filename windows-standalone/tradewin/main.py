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

from tradewin.app import MainWindow
from tradewin.themes import apply_theme


def _start_backend() -> None:
    """在 daemon 线程中启动 FastAPI 服务（localhost:9119）。"""
    import uvicorn
    from trade.app import create_app, serve_trade_chat, _install_cors

    app = create_app()
    serve_trade_chat(app)
    _install_cors(app, 9119)
    uvicorn.run(app, host="127.0.0.1", port=9119, log_level="warning")


def main() -> None:
    """主入口：启动后端 → 初始化 Qt → 显示主窗口 → 进入事件循环。"""
    # 1) 后台线程启动 FastAPI
    _thread = threading.Thread(target=_start_backend, daemon=True)
    _thread.start()

    # 2) 初始化 Qt Application
    _qt_app = QApplication(sys.argv)
    _qt_app.setApplicationName("TradeWin")
    _qt_app.setOrganizationName("SmartTradeAI")
    apply_theme(_qt_app)

    # 3) 创建并显示主窗口
    _window = MainWindow()
    _window.show()

    # 4) 进入 Qt 事件循环
    sys.exit(_qt_app.exec())


if __name__ == "__main__":
    main()
