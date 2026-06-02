"""
Trade AI Assistant — FastAPI application factory.

不依赖 Hermes 初始化副作用，可被 pytest 安全导入。
"""

import os
import secrets
import subprocess as _sp
from pathlib import Path

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# ── Database initialization ──────────────────────────────────────────────────


def _init_db():
    """初始化/迁移数据库，返回数据库路径。"""
    from trade.database import init_db as _do_init
    return _do_init()


def _check_license():
    """检查许可证，返回 (ok, message)。"""
    from trade.license import check_license
    return check_license()


# ── Session token ────────────────────────────────────────────────────────────

_SESSION_TOKEN = secrets.token_urlsafe(32)


def _install_cors(app: FastAPI, port: int) -> None:
    """根据实际监听端口注册 CORS 中间件（仅本机）。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
        ],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["X-Hermes-Session-Token", "X-Company-ID", "Content-Type"],
    )


# ── Hermes Gateway ────────────────────────────────────────────────────────────


def _is_gateway_running() -> bool:
    """检查是否有 Hermes Gateway 进程在运行（跨平台）。"""
    try:
        if os.name == "nt":
            import socket as _sock
            s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
            try:
                s.settimeout(1)
                s.connect(("127.0.0.1", 8642))
                s.close()
                return True
            except OSError:
                return False
            finally:
                s.close()
        else:
            result = _sp.run(
                ["pgrep", "-f", "hermes.*gateway"],
                capture_output=True, text=True, timeout=3,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def _ensure_gateway_running() -> None:
    """如果 Gateway 未运行，启动它。Gateway 独立于 Trade 生命周期。"""
    if _is_gateway_running():
        print("  Hermes Gateway → running (cron scheduler active)")
        return

    try:
        import shutil
        hermes_bin = shutil.which("hermes") or "hermes"
        kwargs = {
            "stdout": _sp.DEVNULL,
            "stderr": _sp.DEVNULL,
        }
        if os.name == "nt":
            kwargs["creationflags"] = 0x00000200  # CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True

        _sp.Popen(
            [hermes_bin, "gateway", "run"],
            env={**os.environ, "GATEWAY_ALLOW_ALL_USERS": "true"},
            **kwargs,
        )
        print("  Hermes Gateway → started (cron scheduler active)")
    except Exception as e:
        print(f"  ⚠️  Hermes Gateway 启动失败: {e}")


# ── System endpoints (无需 session token) ────────────────────────────────────


def _create_system_router() -> APIRouter:
    """创建系统管理路由（更新/备份/重启），不需要 session token。"""
    from trade.api.cron import _capture_output

    router = APIRouter(tags=["system"])

    @router.post("/system/update")
    def api_update_trade():
        """一键更新 Trade 系统。"""
        from trade.post_install import update_trade as _do_update
        return _capture_output(_do_update)

    @router.post("/system/backup")
    def api_backup_trade():
        """备份 Trade 数据为 tar.gz。"""
        from trade.post_install import backup_trade as _do_backup
        return _capture_output(_do_backup)

    @router.post("/system/restart")
    def api_restart_trade():
        """重启 Trade 服务（跨平台）。"""
        trade_home = Path.home() / ".trade" / "data"
        pid_file = trade_home / "trade.pid"
        old_pid = None
        if pid_file.is_file():
            try:
                old_pid = int(pid_file.read_text().strip())
            except (ValueError, OSError):
                pass

        if old_pid is not None:
            import signal
            # 安全校验：确认 PID 属于 trade 进程，防止误杀
            try:
                proc_cmd = Path(f"/proc/{old_pid}/cmdline").read_text() if os.name != "nt" else ""
            except Exception:
                proc_cmd = ""
            is_trade = "trade" in proc_cmd.lower() or "server.py" in proc_cmd.lower()
            if is_trade or not proc_cmd:
                try:
                    os.kill(old_pid, signal.SIGTERM)
                except OSError:
                    pass
            try:
                pid_file.unlink(missing_ok=True)
            except Exception:
                pass

        return {"ok": True, "message": "重启指令已发送"}

    return router


# ── App factory ──────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。

    可在测试中导入以创建独立 app 实例。
    """
    app = FastAPI(title="Foreign Trade Assistant")

    # 数据库初始化
    _db_path = _init_db()
    print(f"  Database: {_db_path}")

    # 许可证检查：到期不影响服务启动（chat 端点在每次请求时校验），
    # 但打印醒目提示引导用户激活
    lic_ok, lic_msg = _check_license()
    if not lic_ok:
        print(f"\n  ⚠️  {lic_msg}")
        print("  Chat 接口已限制，请通过前端获取激活码。\n")

    # 注入 session token
    from trade.api.deps import set_session_token
    set_session_token(_SESSION_TOKEN)

    # 挂载 license 路由（无需 session token）
    from trade.api.license import router as license_router
    app.include_router(license_router, prefix="/api/trade")

    # 挂载 system 路由（无需 session token）
    app.include_router(_create_system_router(), prefix="/api/trade")

    # 挂载 Trade API 路由
    from trade.api import router as trade_router
    app.include_router(trade_router, prefix="/api/trade")

    # Health check
    @app.get("/api/status", include_in_schema=False)
    async def status():
        return {"status": "ok", "app": "Foreign Trade Assistant"}

    return app


def serve_trade_chat(app: FastAPI) -> None:
    """注册 /trade SPA 路由（需要 app 实例和 _SESSION_TOKEN）。"""
    _TRADE_CHAT_HTML = Path(__file__).resolve().parent.parent / "static" / "trade_chat.html"

    @app.get("/trade", response_class=HTMLResponse, include_in_schema=False)
    async def trade_chat_ui():
        """Serve the B2B chat interface with session token injected."""
        if not _TRADE_CHAT_HTML.exists():
            return HTMLResponse(
                content='<html><body style="font-family:sans-serif;padding:2rem;"><h1>Trade chat UI not found</h1><p>The frontend file <code>static/trade_chat.html</code> is missing.</p></body></html>',
                status_code=404,
            )
        html = _TRADE_CHAT_HTML.read_text(encoding="utf-8")
        html = html.replace("__TRADE_SESSION_TOKEN__", _SESSION_TOKEN)
        return HTMLResponse(content=html)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    """`trade` console script 入口 + `python server.py` 入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="Foreign Trade Assistant")
    parser.add_argument("--port", type=int, default=9119)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-gateway", action="store_true", help="不检查/启动 Hermes Gateway")
    args = parser.parse_args()

    # 写入 PID 文件
    import atexit
    pid_dir = Path.home() / ".trade" / "data"
    pid_dir.mkdir(parents=True, exist_ok=True)
    pid_file = pid_dir / "trade.pid"
    pid_file.write_text(str(os.getpid()))
    atexit.register(lambda: pid_file.unlink(missing_ok=True))

    app = create_app()
    serve_trade_chat(app)
    _install_cors(app, args.port)

    if not args.no_gateway:
        _ensure_gateway_running()

    url = f"http://{args.host}:{args.port}/trade"
    print(f"\n  Foreign Trade Assistant → {url}")
    print(f"  Session token: {_SESSION_TOKEN[:8]}...（完整 token 已注入 API 页面）")
    print()

    if not args.no_browser:
        import threading
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
