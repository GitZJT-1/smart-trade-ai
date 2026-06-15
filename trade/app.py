"""
Trade AI Assistant — FastAPI application factory.

不依赖 Hermes 初始化副作用，可被 pytest 安全导入。
"""

import os
import secrets
import subprocess as _sp
import sys
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Depends, FastAPI
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

# ── GitHub latest-version 缓存（TTL 10 分钟）──────────────────────────────
# 避免 /api/status 每次请求都调 GitHub API，在 _waitForRestartAndReload
# 轮询期间（最多 90 次 × 2s = 3min）触发 API 限流（60 次/小时）。
_latest_version_cache: dict = {"value": None, "ts": 0.0}
_LATEST_VERSION_TTL = 600  # 10 分钟


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
            env={**os.environ},
            **kwargs,
        )
        print("  Hermes Gateway → started (cron scheduler active)")
    except Exception as e:
        print(f"  ⚠️  Hermes Gateway 启动失败: {e}")


def _get_trade_data_dir() -> Path:
    """返回 Trade 数据目录（跨平台），与 database._get_db_path 逻辑一致。"""
    trade_home = os.environ.get("TRADE_HOME", "").strip()
    if not trade_home:
        if os.name == "nt":
            _local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            trade_home = str(Path(_local) / "trade")
        else:
            trade_home = str(Path.home() / ".trade")
    return Path(trade_home) / "data"


def _kill_gateway() -> None:
    """终止当前 Hermes Gateway 进程（升级/重启时调用，新进程会重启它）。

    跨平台：Unix 用 pgrep+SIGTERM，Windows 用 taskkill 按命令行匹配。
    失败静默——Gateway 是独立进程，杀不掉也不影响主服务重启。
    """
    try:
        if os.name == "nt":
            # Windows: taskkill 不直接支持命令行匹配，回退到通过端口找进程
            # （需 psutil；没有就跳过——下次启动时新 Trade 启动会判端口已占用而跳过启动新 Gateway）
            try:
                import psutil
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        cmdline = " ".join(proc.info.get("cmdline") or [])
                        if "hermes" in cmdline.lower() and "gateway" in cmdline.lower():
                            proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                pass
        else:
            _sp.run(
                ["pkill", "-TERM", "-f", "hermes.*gateway"],
                capture_output=True, timeout=5,
            )
    except Exception:
        # 杀 Gateway 失败不阻塞主流程
        pass


def _perform_restart() -> None:
    """终止当前 Trade 进程并以独立子进程启动新实例。

    关键设计：先启动新进程，再杀旧进程——避免 SIGTERM 杀掉自己后 Popen 执行不到。
    新进程启动后会自动重试绑定端口（uvicorn 的 SO_REUSEADDR），等旧进程退出后即可接管。

    供 /system/restart 直接调用，也供 /system/update 在响应返回后通过
    BackgroundTasks 触发——这样升级完成的响应能先送达前端。
    """
    import signal as _signal
    import sys as _sys

    trade_data = _get_trade_data_dir()
    pid_file = trade_data / "trade.pid"
    old_pid = None
    if pid_file.is_file():
        try:
            old_pid = int(pid_file.read_text().strip())
        except (ValueError, OSError):
            pass

    # 在杀自己之前必须先记录启动命令，否则 kill 后访问不到
    _restart_cmd = [_sys.executable] + _sys.argv

    # 1. 先杀 Gateway（独立进程，新 Trade 启动时会重新拉起）
    _kill_gateway()

    # 2. 先启动新进程（在杀旧进程之前！），新进程的 uvicorn 会重试绑定端口
    _popen_kwargs = {
        "stdout": _sp.DEVNULL,
        "stderr": _sp.DEVNULL,
    }
    if os.name == "nt":
        _popen_kwargs["creationflags"] = 0x00000200  # CREATE_NEW_PROCESS_GROUP
    else:
        _popen_kwargs["start_new_session"] = True
    _sp.Popen(_restart_cmd, **_popen_kwargs)

    # 3. 再杀旧进程（新进程已经启动，不怕这里被 SIGTERM 打断）
    if old_pid is not None:
        # 三层 PID 校验：psutil 优先，回退 /proc，防止 PID 重用误杀
        # 第三层：以上皆不可用（如 macOS 既无 psutil 也无 /proc），信任自己的 PID 文件
        is_trade = False
        _verified = False
        try:
            import psutil
            proc = psutil.Process(old_pid)
            cmdline = " ".join(proc.cmdline())
            is_trade = (
                ("server.py" in cmdline and "trade" in cmdline)
                or "trade" in cmdline
            )
            if is_trade:
                try:
                    my_exe = Path(_sys.executable).resolve()
                    proc_exe = Path(proc.exe()).resolve()
                    if my_exe != proc_exe:
                        is_trade = False
                except Exception:
                    pass
            _verified = True
        except ImportError:
            try:
                proc_cmd = Path(f"/proc/{old_pid}/cmdline").read_text() if os.name != "nt" else ""
                is_trade = "trade" in proc_cmd.lower() or "server.py" in proc_cmd.lower()
                _verified = True
            except Exception:
                pass
        except Exception:
            pass

        # 如果两个校验手段都不可用（如 macOS），信任自己的 PID 文件直接杀
        if not _verified:
            is_trade = True

        if is_trade:
            try:
                os.kill(old_pid, _signal.SIGTERM)
            except OSError:
                pass  # 进程已不存在
        try:
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass


# ── System endpoints (无需 session token) ────────────────────────────────────


def _create_system_router() -> APIRouter:
    """创建系统管理路由（更新/备份/重启），需要 session token 认证。"""
    from fastapi import BackgroundTasks

    from trade.api.cron import _capture_output
    from trade.api.deps import require_session

    router = APIRouter(tags=["system"], dependencies=[Depends(require_session)])

    @router.post("/system/update")
    def api_update_trade(background_tasks: BackgroundTasks):
        """一键更新 Trade 系统。

        升级成功后通过 BackgroundTasks 调度全量重启——这样响应能先送达前端，
        前端拿到 restart_scheduled=True 后开始轮询服务状态，等待重启完成。
        """
        from trade.post_install import update_trade as _do_update
        result = _capture_output(_do_update)
        output = result.get("output", "")

        # 检测 update_trade 输出中的致命失败标记（⚠️ 不纳入——模板同步/自启动失败不影响升级）
        _failed = any(marker in output for marker in [
            "❌", "update failed", "git pull failed", "pip install failed",
            "git stash 也失败", "Database check failed",
        ])

        if result.get("ok") and not _failed:
            # 升级成功后立即使 GitHub 版本缓存失效，下次 /api/status 强制重新拉取
            _latest_version_cache["ts"] = 0.0
            background_tasks.add_task(_perform_restart)
            result["restart_scheduled"] = True
        else:
            result["ok"] = False
            if _failed:
                result["error"] = "更新失败，请查看 output 了解详情"
        return result

    @router.post("/system/backup")
    def api_backup_trade():
        """备份 Trade 数据为 tar.gz。"""
        from trade.post_install import backup_trade as _do_backup
        return _capture_output(_do_backup)

    @router.post("/system/restart")
    def api_restart_trade():
        """重启 Trade 服务（跨平台）。

        委托给 _perform_restart()——含三层 PID 安全校验和 Gateway 协同重启。
        """
        _perform_restart()
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

    # 挂载 system 路由（需要 session token）
    app.include_router(_create_system_router(), prefix="/api/trade")

    # 挂载 Trade API 路由
    from trade.api import router as trade_router
    app.include_router(trade_router, prefix="/api/trade")

    # Health check
    @app.get("/api/status", include_in_schema=False)
    async def status():
        # 读取当前版本号（从 pyproject.toml）
        version = "0.0.0"
        try:
            import tomllib as _toml
        except ImportError:
            import tomli as _toml
        try:
            pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
            data = _toml.loads(pyproject.read_text())
            version = data.get("project", {}).get("version", version)
        except Exception:
            pass

        # 用缓存降低 GitHub API 调用频率，防止限流导致版本检测失效
        import time as _time
        _now = _time.monotonic()
        if (_latest_version_cache["value"] is not None
                and _now - _latest_version_cache["ts"] < _LATEST_VERSION_TTL):
            latest = _latest_version_cache["value"]
        else:
            import asyncio as _asyncio

            def _fetch_latest_version() -> str:
                import urllib.request as _ur
                try:
                    _req = _ur.Request(
                        "https://api.github.com/repos/chefroger/smart-trade-ai/releases/latest",
                        headers={"Accept": "application/vnd.github+json", "User-Agent": "Trade-Status/1.0"},
                    )
                    with _ur.urlopen(_req, timeout=5) as _resp:
                        import json as _json
                        _data = _json.loads(_resp.read().decode())
                        return _data.get("tag_name", "").lstrip("v")
                except Exception:
                    return ""

            latest = await _asyncio.get_event_loop().run_in_executor(None, _fetch_latest_version)
            # 仅在 GitHub API 调用成功时更新缓存（失败时 keep 旧值，宁可短暂不一致）
            if latest:
                _latest_version_cache["value"] = latest
                _latest_version_cache["ts"] = _time.monotonic()

        return {
            "status": "ok",
            "app": "Foreign Trade Assistant",
            "version": version,
            "latest_version": latest or None,
        }

    return app


def serve_trade_chat(app: FastAPI) -> None:
    """注册 /trade SPA 路由（需要 app 实例和 _SESSION_TOKEN）。"""
    # PyInstaller 打包后资源文件在 _MEIPASS 目录中
    if getattr(sys, "frozen", False):
        _STATIC_DIR = Path(sys._MEIPASS) / "static"
    else:
        _STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
    _TRADE_CHAT_HTML = _STATIC_DIR / "trade_chat.html"

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

    # 写入 PID 文件（0600 权限防止被其他用户篡改）
    import atexit
    pid_dir = _get_trade_data_dir()
    pid_dir.mkdir(parents=True, exist_ok=True)
    pid_file = pid_dir / "trade.pid"
    pid_file.write_text(str(os.getpid()))
    if os.name != "nt":
        pid_file.chmod(0o600)
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

    # 重启场景：旧进程可能仍在占用端口，uvicorn.run 会因 [Errno 48] 失败。
    # 用重试循环等待旧进程退出后端口释放，最多等 10 秒。
    import time as _time
    for _attempt in range(20):
        try:
            uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
            break
        except OSError as _e:
            if "Address already in use" in str(_e) or _e.errno == 48:
                if _attempt == 0:
                    print("  ⏳ 等待旧进程释放端口...")
                _time.sleep(0.5)
                continue
            raise
