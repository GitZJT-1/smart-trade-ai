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


def _start_backend() -> None:
    """在 daemon 线程中启动 FastAPI 服务（localhost:9119）。"""
    import uvicorn
    from trade.app import create_app, serve_trade_chat, _install_cors

    app = create_app()
    serve_trade_chat(app)
    _install_cors(app, 9119)
    uvicorn.run(app, host="127.0.0.1", port=9119, log_level="warning")


def main() -> None:
    """主入口：启动后端 → 启动 Qt GUI。"""
    # 1) 后台线程启动 FastAPI
    _thread = threading.Thread(target=_start_backend, daemon=True)
    _thread.start()

    # 2) 初始化 Qt Application
    _qt_app = QApplication(sys.argv)
    _qt_app.setApplicationName("TradeWin")
    _qt_app.setOrganizationName("SmartTradeAI")

    # 3) 进入 Qt 事件循环（后续 Task 会添加主窗口）
    print("TradeWin started. Backend running on http://127.0.0.1:9119")
    sys.exit(_qt_app.exec())


if __name__ == "__main__":
    main()
