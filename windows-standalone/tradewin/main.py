"""
TradeWin 入口。

启动流程:
  1. 检测 Hermes Agent 是否安装 → 未安装则自动 pip install
  2. 检测 Trade 数据库是否初始化 → 未初始化则启动首次运行向导
     a. 选择 LLM 提供商（OpenAI / Anthropic / MiniMax / DeepSeek / Moonshot）
     b. 输入 API Key + Tavily Key
     c. 自动安装 Skills → 初始化数据库 → 写入配置文件
  3. 后台线程启动 FastAPI (localhost:9119)
  4. Qt GUI 启动 → 主窗口 → 托盘 → 事件循环
"""

import sys
import threading
from pathlib import Path

# 将父项目根目录加入 sys.path，使 trade 包可导入
_parent = Path(__file__).resolve().parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from PySide6.QtWidgets import QApplication, QMessageBox


def _start_backend() -> None:
    """在 daemon 线程中启动 FastAPI 服务（localhost:9119）。"""
    import uvicorn

    from trade.app import _install_cors, create_app, serve_trade_chat

    app = create_app()
    serve_trade_chat(app)
    _install_cors(app, 9119)
    uvicorn.run(app, host="127.0.0.1", port=9119, log_level="warning")


def _run_first_run_wizard() -> dict | None:
    """运行首次配置向导，返回用户选择的配置。

    返回格式: {"provider": str, "api_key": str, "tavily_key": str}
    用户取消或关闭向导时返回 None。
    """
    from tradewin.wizard import FirstRunWizard

    wizard = FirstRunWizard()
    if wizard.exec() == FirstRunWizard.Accepted:
        return wizard.get_config()
    return None


def main() -> None:
    """主入口：环境自举 → 后端 → GUI。"""
    # ── 步骤 0: 初始化 QApplication（向导也需要 Qt） ─────────────────────
    _qt_app = QApplication(sys.argv)
    _qt_app.setApplicationName("TradeWin")
    _qt_app.setOrganizationName("SmartTradeAI")

    # ── 步骤 1: 检查 Hermes Agent ────────────────────────────────────────
    from tradewin.setup import (
        install_hermes,
        is_api_key_configured,
        is_hermes_installed,
        is_trade_initialized,
    )

    if not is_hermes_installed():
        reply = QMessageBox.question(
            None, "安装 Hermes Agent",
            "TradeWin 需要 Hermes Agent（AI 引擎）才能工作。\n\n"
            "是否立即自动安装？（需要网络连接，约 1 分钟）",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok = install_hermes(
                progress_callback=lambda msg: print(f"  {msg}")
            )
            if not ok:
                QMessageBox.critical(
                    None, "安装失败",
                    "Hermes Agent 安装失败。\n"
                    "请检查网络连接后重试，或手动运行: pip install hermes-agent"
                )
                sys.exit(1)
        else:
            QMessageBox.information(
                None, "提示",
                "请手动安装 Hermes Agent 后重新启动 TradeWin:\n"
                "  pip install hermes-agent"
            )
            sys.exit(0)

    # ── 步骤 2: 检查首次运行 ─────────────────────────────────────────────
    need_wizard = False
    need_skills = True
    need_db = False

    if not is_trade_initialized():
        need_wizard = True
        need_db = True
    elif not is_api_key_configured():
        need_wizard = True

    if need_wizard:
        # 显示首次运行向导
        w = _run_first_run_wizard()  # 返回 None → 用户取消了
        if w is None:
            # 程序继续运行但功能受限（用户可能只想试一下）
            need_skills = not is_trade_initialized()
            need_db = not is_trade_initialized()
        else:
            # 用户完成了向导 → 执行安装步骤
            from tradewin.setup import (
                init_trade_database,
                install_trade_skills,
                write_hermes_config,
                write_hermes_env,
            )

            # 安装 Skills
            install_trade_skills()
            need_skills = False

            # 初始化数据库
            init_trade_database()
            need_db = False

            # 写入配置文件
            api_key = w.get("api_key", "")
            if api_key:
                write_hermes_env(
                    w.get("provider", "openai"),
                    api_key,
                    w.get("tavily_key", ""),
                )
                write_hermes_config(w.get("provider", "openai"))

    # 如果向导跳过了但 skills 还没装
    if need_skills:
        from tradewin.setup import install_trade_skills
        install_trade_skills()

    if need_db:
        from tradewin.setup import init_trade_database
        init_trade_database()

    # ── 步骤 3: 启动 FastAPI 后端 ────────────────────────────────────────
    _thread = threading.Thread(target=_start_backend, daemon=True)
    _thread.start()

    # ── 步骤 4: 初始化 Qt GUI ────────────────────────────────────────────
    from tradewin.themes import apply_theme
    apply_theme(_qt_app)

    from tradewin.app import MainWindow
    _window = MainWindow()
    _window.show()

    # ── 步骤 5: 系统托盘 ─────────────────────────────────────────────────
    from tradewin.tray import TrayManager
    _tray = TrayManager(_qt_app, _window)

    def _close_to_tray(event):
        event.ignore()
        _window.hide()
        _tray.show_notification("TradeWin", "已最小化到系统托盘")

    _window.closeEvent = _close_to_tray

    # ── 步骤 6: 进入事件循环 ─────────────────────────────────────────────
    sys.exit(_qt_app.exec())


if __name__ == "__main__":
    main()
