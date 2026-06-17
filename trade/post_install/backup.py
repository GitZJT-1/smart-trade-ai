"""
Trade AI Assistant — 系统数据备份与还原。

备份范围：
  - ~/.trade/data/trade.db（SQLite 数据库）
  - ~/.trade/companies/{slug}/（公司数据目录）
  - ~/.trade/prompts/（系统提示词文件）
  - ~/.hermes/memories/（Hermes 记忆文件）
  - ~/.hermes/skills/b2b-*/（B2B skill 定义）

输出格式：tar.gz 压缩包，文件名格式 trade-backup-YYYY-MM-DD-HHMM.tar.gz
"""

from __future__ import annotations

import shutil
import subprocess as _sp
import sys
import tarfile
import tempfile
from datetime import datetime as _real_datetime
from pathlib import Path

from trade.post_install.skills import _get_hermes_home, _get_trade_home

# ── 系统备份 ──────────────────────────────────────────────────────────────

def backup_trade(output_dir: str | None = None) -> str:
    """备份 Trade 系统数据为 tar.gz 压缩包。

    备份内容：
      - SQLite 数据库（仅有该文件即是最小可恢复备份）
      - 公司数据目录（companies/）
      - 系统提示词（prompts/）
      - Hermes 记忆文件（.md / .json / .txt）
      - B2B skill 定义（SKILL.md）

    Args:
        output_dir: 输出目录（默认桌面）

    Returns:
        生成的 tar.gz 文件绝对路径
    """
    import datetime

    if output_dir is None:
        # 未指定输出目录时默认使用桌面
        desktop = Path.home() / "Desktop"
        if not desktop.is_dir():
            desktop = Path.home() / "桌面"  # macOS 中文桌面
        if not desktop.is_dir():
            desktop = Path.home()  # 桌面不存在时回退到 home
        output_dir = str(desktop)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"trade-backup-{timestamp}.tar.gz"
    out_path = Path(output_dir) / filename

    trade_home = _get_trade_home()
    hermes_home = _get_hermes_home()

    # 收集需要打包的文件路径列表
    sources: list[tuple[Path, str]] = []  # (绝对路径, tar 内的 arcname)

    # 1) SQLite 数据库：最关键的备份目标
    db_path = trade_home / "data" / "trade.db"
    if db_path.is_file():
        sources.append((db_path, ".trade/data/trade.db"))

    # 2) 公司数据目录：递归收集所有文件
    companies_dir = trade_home / "companies"
    if companies_dir.is_dir():
        for company_dir in companies_dir.iterdir():
            if company_dir.is_dir():
                for f in company_dir.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(trade_home))
                        sources.append((f, f".trade/{rel}"))

    # 3) 系统提示词（prompts/system.md 等）
    prompts_dir = trade_home / "prompts"
    if prompts_dir.is_dir():
        for f in prompts_dir.rglob("*"):
            if f.is_file():
                sources.append((f, f".trade/{f.relative_to(trade_home)}"))

    # 4) Hermes 记忆文件（.md / .json / .txt）
    memories_dir = hermes_home / "memories"
    if memories_dir.is_dir():
        for f in memories_dir.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".json", ".txt"):
                sources.append(
                    (f, f".hermes/memories/{f.relative_to(memories_dir)}")
                )

    # 5) B2B skill 定义（每个 b2b-* 目录下的 SKILL.md）
    skills_dir = hermes_home / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and skill_dir.name.startswith("b2b-"):
                skill_md = skill_dir / "SKILL.md"
                if skill_md.is_file():
                    sources.append(
                        (skill_md, f".hermes/skills/{skill_dir.name}/SKILL.md")
                    )

    if not sources:
        print("[backup] WARNING: No data found to backup.")
        sys.exit(1)

    # 打包为 tar.gz
    print(f"[backup] Packaging {len(sources)} files ...")
    with tarfile.open(out_path, "w:gz") as tar:
        for abs_path, arcname in sources:
            tar.add(str(abs_path), arcname=arcname)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"[backup] Done: {out_path} ({size_mb:.1f} MB)")
    return str(out_path)


# ── 系统还原 ──────────────────────────────────────────────────────────────

def restore_trade(backup_file: str = "") -> str:
    """从 tar.gz 备份文件还原系统数据。

    还原步骤：
      1. 解压 tar.gz 到临时目录
      2. SQLite 完整性检查（PRAGMA integrity_check）
      3. 备份当前数据（trade-before-restore-{timestamp}.db）
      4. 替换 data/ + companies/
      5. 重启 Trade 服务

    Args:
        backup_file: tar.gz 备份文件路径

    Returns:
        还原结果消息
    """
    src = Path(backup_file)
    if not src.is_file():
        return f"✗ 备份文件不存在: {backup_file}"

    trade_home = _get_trade_home()

    # 步骤 1: 解压到临时目录
    print(f"[restore] 解压 {src.name} ...")
    tmp_dir = Path(tempfile.mkdtemp(prefix="trade-restore-"))
    try:
        _sp.run(["tar", "-xzf", str(src), "-C", str(tmp_dir)], check=True)
    except _sp.CalledProcessError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return f"✗ 解压失败: {e}"

    # 步骤 2: SQLite 完整性检查
    db_candidates = list(tmp_dir.rglob("trade.db"))
    if not db_candidates:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return "✗ 备份中未找到 trade.db"

    db_file = db_candidates[0]
    result = _sp.run(
        ["sqlite3", str(db_file), "PRAGMA integrity_check"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or "ok" not in result.stdout.lower():
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return f"✗ 数据库完整性检查失败: {result.stdout.strip()}"

    print("[restore] 数据库完整性检查通过")

    # 步骤 3: 备份当前数据（还原前保护措施）
    backup_ts = _real_datetime.now().strftime("%Y%m%d-%H%M%S")
    current_db = trade_home / "data" / "trade.db"
    shutil.copy2(
        current_db,
        trade_home / "data" / f"trade-before-restore-{backup_ts}.db",
    )

    # 步骤 4: 替换数据库
    restored_db = tmp_dir / "data" / "trade.db"
    if restored_db.exists():
        shutil.copy2(str(restored_db), str(current_db))
    else:
        shutil.copy2(str(db_file), str(current_db))

    # 替换 companies 目录（如果备份中有）
    restored_companies = tmp_dir / "companies"
    if restored_companies.exists():
        companies_dst = trade_home / "companies"
        companies_dst.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            str(restored_companies), str(companies_dst), dirs_exist_ok=True
        )

    shutil.rmtree(tmp_dir, ignore_errors=True)

    # 步骤 5: 重启服务
    print("[restore] 数据已还原，正在重启服务 ...")
    _restart_trade_service()

    return f"✓ 已从 {src.name} 还原，服务已重启"


# ── 服务重启（跨平台） ────────────────────────────────────────────────────

def _restart_trade_service() -> None:
    """重启 Trade 服务进程（跨平台实现）。

    重启策略（按优先级）：
      1. 通过 PID 文件查找旧进程 → kill + 重新启动（推荐）
      2. launchd (macOS) → unload + load plist
      3. systemd (Linux) → systemctl --user restart
      4. 打印手动操作指引（所有自动方式都失败时）

    注意：此函数用于 restore 场景。正常升级/重启走 app.py 的
    _perform_restart()（独立 shell 子进程方式）。
    """
    import platform
    import signal as _signal
    import time as _time_module

    sys_name = platform.system()

    # ── 策略 1：通过 PID 文件终止旧进程，然后启动新进程 ──
    trade_home = _get_trade_home()
    pid_file = trade_home / "data" / "trade.pid"
    old_pid = None
    if pid_file.is_file():
        try:
            _pid_text = pid_file.read_text().strip()
            if _pid_text:
                old_pid = int(_pid_text)
        except (ValueError, OSError):
            pass  # PID 文件损坏或无内容，跳过 kill 步骤

    if old_pid is not None:
        try:
            if sys_name == "Windows":
                # Windows: taskkill 终止进程树
                _sp.run(
                    ["taskkill", "/PID", str(old_pid), "/T", "/F"],
                    capture_output=True, timeout=10,
                )
            else:
                # Unix: SIGTERM 优雅终止 → 等 2 秒 → SIGKILL 强制终止
                _os_module = __import__("os")
                _os_module.kill(old_pid, _signal.SIGTERM)
                _waited = 0
                for _ in range(20):  # 最多等 2 秒（20 × 0.1s）
                    _time_module.sleep(0.1)
                    _waited += 0.1
                    try:
                        _os_module.kill(old_pid, 0)  # 信号 0 = 检查进程是否存活
                    except OSError:
                        break  # 进程已退出
                else:
                    # 进程仍在运行，SIGKILL 强制终止
                    try:
                        _os_module.kill(old_pid, _signal.SIGKILL)
                    except OSError:
                        pass  # 进程可能已经不存在
        except Exception:
            pass  # 进程可能已经不存在，不阻塞后续重启
        finally:
            # 清理旧 PID 文件（无论 kill 成功与否）
            try:
                pid_file.unlink()
            except OSError:
                pass

    # ── 策略 2：重新启动 Trade（继承原始启动参数） ──
    cmd = _build_restart_command()
    try:
        kwargs = {
            "stdout": _sp.DEVNULL,
            "stderr": _sp.DEVNULL,
        }
        if sys_name == "Windows":
            kwargs["creationflags"] = 0x00000200  # CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True  # 独立进程会话，脱离父进程生命周期
        _sp.Popen(cmd, **kwargs)
        print("  ↻ Trade 服务已重新启动")
        return
    except Exception as e:
        print(f"  ⚠ 自动重启失败: {e}")

    # ── 策略 3：launchd (macOS) / systemd (Linux) ──
    label = "com.trade.assistant"

    if sys_name == "Darwin":
        _try_launchd_restart(label)
        return

    if sys_name == "Linux":
        _try_systemd_restart(label)
        return

    # ── 策略 4：无法自动重启，打印手动指引 ──
    _print_manual_restart_instructions(sys_name, label)


def _build_restart_command() -> list[str]:
    """根据当前进程的启动方式，推断并构建重启命令。

    支持三种启动方式：
      - python server.py（直接运行脚本）
      - python -m trade（通过包模块启动）
      - trade（console_scripts 入口）
    """
    # 通过 sys.argv 推断启动方式
    if len(sys.argv) > 0 and "server.py" in sys.argv[0]:
        # python server.py 方式 → 复用同路径
        server_py = Path(sys.argv[0]).resolve()
        if server_py.is_file():
            return [sys.executable, str(server_py)]
        return [sys.executable, "-m", "trade"]  # fallback
    return [sys.executable, "-m", "trade"]  # 默认：包模块启动


def _try_launchd_restart(label: str) -> None:
    """尝试通过 macOS launchd 重启服务。"""
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    if not plist.exists():
        return

    _launchctl = shutil.which("launchctl") or "/bin/launchctl"
    try:
        _sp.run(
            [_launchctl, "unload", str(plist)],
            capture_output=True, timeout=10,
        )
        _sp.run(
            [_launchctl, "load", str(plist)],
            capture_output=True, timeout=10,
        )
        print("  ↻ Trade 后台服务已重新加载（launchd）")
    except Exception:
        pass  # launchd 失败时静默 fallthrough


def _try_systemd_restart(label: str) -> None:
    """尝试通过 Linux systemd user unit 重启服务。"""
    for cmd in (
        ["systemctl", "--user", "restart", label],
        ["sudo", "systemctl", "restart", label],
    ):
        r = _sp.run(cmd, capture_output=True, timeout=10)
        if r.returncode == 0:
            print("  ↻ Trade 后台服务已重新启动（systemd）")
            return


def _print_manual_restart_instructions(sys_name: str, label: str) -> None:
    """当所有自动重启方式都失败时，打印明确的手动操作指引。"""
    print("  💡 Trade 代码已更新。请重启 Trade 以应用更改：")
    if sys_name == "Windows":
        print("     关闭当前 Trade 窗口后重新运行 trade 命令")
    elif sys_name == "Darwin":
        print(f"     launchctl unload ~/Library/LaunchAgents/{label}.plist")
        print(f"     launchctl load ~/Library/LaunchAgents/{label}.plist")
        print("     或手动运行: trade")
    else:
        print(f"     systemctl --user restart {label}")
        print("     或手动运行: trade")
