"""
post_install: 将 Trade B2B skills 安装到 Hermes skills 目录。

调用方式：
  - `pip install -e .` 或 `pip install .`（setuptools 安装后自动执行）
  - 手动执行：`install-trade-skills`（声明为项目 console script）

本模块在包导入图之外运行——只使用标准库，
避免包与 hermes-agent 之间的版本/导入冲突。

它从以下位置复制 skills：
  {package_location}/skills/b2b-*/
  → ~/.hermes/skills/b2b-*/

Hermes 从 ~/.hermes/skills/ 发现 skills（通过 get_all_skills_dirs()）。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _get_hermes_home() -> Path:
    """镜像 hermes_constants.get_hermes_home()，无导入依赖。"""
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        # 如果设置了 HERMES_HOME 环境变量，优先使用
        return Path(val)
    return Path.home() / ".hermes"


def _get_trade_home() -> Path:
    """返回用户 Trade 数据目录（与 database.py / company.py / prompts.py 统一）。

    Priority: TRADE_HOME env var → platform default.
    macOS/Linux: ~/.trade/, Windows: %LOCALAPPDATA%\trade\
    """
    val = os.environ.get("TRADE_HOME", "").strip()
    if val:
        # 如果设置了 TRADE_HOME 环境变量，优先使用
        return Path(val)
    if os.name == "nt":
        # Windows 系统下使用 %LOCALAPPDATA%\trade\
        local_appdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local_appdata) / "trade"
    # macOS/Linux 默认路径
    return Path.home() / ".trade"


def _get_package_skills_dir() -> Path | None:
    """查找已安装包的 skills 目录。

    通过 `pip install -e .` 或 `pip install .` 从仓库安装时，
    包根目录可以通过 __main__ 或 trade 包的 __file__ 发现。
    如果找不到则回退到搜索 sys.path。
    """
    # 尝试通过 trade 包的 __file__ 定位（例如 .../site-packages/trade/__init__.py）
    for prefix in list(sys.path):
        p = Path(prefix)
        if not p.is_dir():
            # 跳过非目录路径
            continue
        candidate = p / "trade" / "__init__.py"
        if candidate.exists():
            skills_dir = candidate.parent.parent / "skills"
            if skills_dir.is_dir():
                return skills_dir

    # 回退：在本脚本所在目录的父级查找 skills 目录（开发模式安装）
    self_dir = Path(__file__).parent.parent  # 项目根目录
    dev_skills = self_dir / "skills"
    if dev_skills.is_dir():
        return dev_skills

    return None


def _copy_skills(src: Path, dst_base: Path) -> list[str]:
    """将 b2b-* skill 目录从 src 复制到 dst_base。

    为每个找到的 skill 创建 dst_base/b2b-{skill-name}/SKILL.md。
    返回已安装的 skill 名称列表。
    """
    installed = []
    for skill_dir in sorted(src.iterdir()):
        if not skill_dir.is_dir():
            # 跳过非目录条目
            continue
        if not skill_dir.name.startswith("b2b-"):
            # 只处理 b2b 前缀的 skill 目录
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            # 跳过没有 SKILL.md 的目录
            continue

        dest = dst_base / skill_dir.name / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_file, dest)
        installed.append(skill_dir.name)

    return installed


def _copy_trade_template(src: Path, dst: Path) -> None:
    """将 .trade-template/ 目录复制到 Trade 运行时目录。

    只复制骨架（空模板文件），不复制运行时数据。
    创建 dst/.trade-template/ 作为运行时副本。

    同时植入 prompts 目录，让用户从第一天起就有可编辑的文件（prompts/system.md）。
    """
    if src.is_dir():
        dest = dst / ".trade-template"
        if not dest.exists():
            # 只在目标不存在时才复制，避免覆盖用户数据
            shutil.copytree(src, dest, dirs_exist_ok=False)
            for f in dest.rglob("*"):
                if f.is_file():
                    f.chmod(0o644)

    # 从模板植入 ~/.trade/prompts/system.md（仅当尚未存在时）
    prompts_src = src / "prompts" / "system.md"
    prompts_dir = dst / "prompts"
    prompts_dst = prompts_dir / "system.md"
    if prompts_src.is_file() and not prompts_dst.is_file():
        # 如果用户已有 prompts 文件则跳过，避免覆盖用户自定义内容
        prompts_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prompts_src, prompts_dst)
        prompts_dst.chmod(0o644)


def install_skills() -> None:
    """主入口：将 Trade skills 安装到 Hermes 并设置 Trade 数据目录。"""
    hermes_home = _get_hermes_home()
    trade_home = _get_trade_home()

    hermes_skills_dir = hermes_home / "skills"

    # 查找包中的 skills 目录
    package_skills = _get_package_skills_dir()
    if package_skills is None:
        # 找不到 skills 目录时报告错误并退出
        print("[post_install] ERROR: Could not find skills directory.", file=sys.stderr)
        print("[post_install] Expected: <package-root>/skills/b2b-*/SKILL.md", file=sys.stderr)
        sys.exit(1)

    # 查找 .trade-template — 与 skills 同级的模板目录
    # 优先从 package_skills 的父目录查找（pip install . 场景）
    # 其次从本脚本所在目录查找（pip install -e . 开发模式）
    template_dir = package_skills.parent / ".trade-template"
    if not template_dir.is_dir():
        # 在 package_skills 旁边找不到，回退到项目根目录
        self_dir = Path(__file__).parent.parent  # 项目根目录（开发模式回退）
        template_dir = self_dir / ".trade-template"

    # 将 skills 复制到 Hermes 目录
    print(f"[post_install] Hermes home:   {hermes_home}")
    print(f"[post_install] Package skills: {package_skills}")
    print(f"[post_install] Hermes skills: {hermes_skills_dir}")

    installed = _copy_skills(package_skills, hermes_skills_dir)

    if installed:
        # 打印成功安装的 skill 列表
        print(f"[post_install] Installed {len(installed)} skills to Hermes:")
        for name in installed:
            print(f"  ✓ {name}")
    else:
        # 没有找到任何 b2b-* skill 时发出警告
        print("[post_install] WARNING: No b2b-* skills found to install.", file=sys.stderr)

    # 在 Trade 运行时目录中设置 .trade-template
    if template_dir.is_dir():
        # 只有模板目录存在时才执行复制
        print(f"[post_install] Trade home:    {trade_home}")
        trade_home.mkdir(parents=True, exist_ok=True)
        _copy_trade_template(template_dir, trade_home)
        print(f"[post_install] Trade data template installed to: {trade_home}/.trade-template")

    print("[post_install] Done.")


def update_skills() -> None:
    """从 GitHub 拉取最新 B2B skill 定义并更新到本地 Hermes 目录。

    和 install_skills 的区别：
      - install_skills: 从本地 pip 安装包中复制 skills（安装时用）
      - update_skills:  从 GitHub main 分支下载最新 SKILL.md（更新时用）

    用法：trade-skills-update（或 python -m trade.post_install update）
    """
    import hashlib
    import urllib.error
    import urllib.request

    hermes_home = _get_hermes_home()
    hermes_skills_dir = hermes_home / "skills"

    # 本地包中的 skills 目录（用于列出需要更新哪些 skill）
    package_skills = _get_package_skills_dir()
    if package_skills is None:
        print("[update_skills] ERROR: Cannot find local skills directory.", file=sys.stderr)
        sys.exit(1)

    # GitHub raw URL 前缀
    RAW_BASE = "https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/skills"

    updated = 0
    skipped = 0
    failed = 0

    for skill_dir in sorted(package_skills.iterdir()):
        if not skill_dir.is_dir() or not skill_dir.name.startswith("b2b-"):
            # 只处理 b2b 前缀的目录，跳过非 skill 条目
            continue

        skill_name = skill_dir.name
        raw_url = f"{RAW_BASE}/{skill_name}/SKILL.md"
        dest_dir = hermes_skills_dir / skill_name
        dest_file = dest_dir / "SKILL.md"

        # 最多重试 3 次（应对 GitHub 偶发的 SSL 超时/丢包）
        _MAX_TRIES = 3
        _tried = 0
        _last_error = None
        while _tried < _MAX_TRIES:
            _tried += 1
            try:
                # 下载 GitHub 上的最新 SKILL.md
                req = urllib.request.Request(
                    raw_url,
                    headers={"User-Agent": "Trade-Skills-Updater/1.0"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    remote_content = resp.read().decode("utf-8")

                # 比较 hash，相同则跳过
                remote_hash = hashlib.sha256(remote_content.encode()).hexdigest()
                if dest_file.is_file():
                    local_hash = hashlib.sha256(dest_file.read_bytes()).hexdigest()
                    if local_hash == remote_hash:
                        print(f"  ✓ {skill_name} (already up-to-date)")
                        skipped += 1
                        break

                # hash 不同或本地文件不存在，写入新内容
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(remote_content, encoding="utf-8")
                print(f"  ↻ {skill_name} (updated)")
                updated += 1
                break

            except urllib.error.HTTPError as e:
                print(f"  ✗ {skill_name} (HTTP {e.code}: {raw_url})", file=sys.stderr)
                failed += 1
                break  # HTTP 错误（如 404）不需要重试
            except Exception as e:
                _last_error = e
                if _tried < _MAX_TRIES:
                    import time as _time
                    _time.sleep(1.0 * _tried)  # 递增退避：1s, 2s
                    continue
                # 重试耗尽
                print(f"  ✗ {skill_name} (error after {_MAX_TRIES} retries: {_last_error})", file=sys.stderr)
                failed += 1

    print(f"\n[update_skills] Done. {updated} updated, {skipped} skipped, {failed} failed.")
    if updated > 0:
        # 有更新时提示需要重启
        print("Hermes will pick up the updated skills on the next request.")


def _restart_trade_service() -> None:
    """重启 Trade 服务进程，支持所有平台。

    策略（按优先级）：
      1. 通过 PID 文件查找运行中的 Trade 进程，发送 SIGTERM / 终止信号
      2. 重新启动 Trade（使用相同的 Python 解释器和命令）
      3. fallback：launchd (macOS) / systemd (Linux)

    如果以上都不可行（例如前台终端运行），打印明确的用户操作指引。
    """
    import platform
    import signal
    import subprocess as _sp
    import time

    sys_name = platform.system()

    # ── 策略 1：通过 PID 文件终止旧进程 ──
    # Trade 进程在启动时将 PID 写入 ~/.trade/data/trade.pid
    trade_home = _get_trade_home()
    pid_file = trade_home / "data" / "trade.pid"
    old_pid = None
    if pid_file.is_file():
        try:
            _pid_text = pid_file.read_text().strip()
            if _pid_text:
                old_pid = int(_pid_text)
        except (ValueError, OSError):
            pass

    if old_pid is not None:
        try:
            if sys_name == "Windows":
                # Windows: 用 taskkill 终止进程树
                _sp.run(
                    ["taskkill", "/PID", str(old_pid), "/T", "/F"],
                    capture_output=True, timeout=10,
                )
            else:
                # Unix: 先尝试优雅终止，等 2 秒后强制 kill
                _os_module = __import__("os")
                _os_module.kill(old_pid, signal.SIGTERM)
                _waited = 0
                for _ in range(20):  # 最多等 2 秒
                    time.sleep(0.1)
                    _waited += 0.1
                    try:
                        _os_module.kill(old_pid, 0)  # 检查进程是否存在
                    except OSError:
                        # 进程已退出
                        break
                else:
                    # 进程仍在运行，强制 kill
                    try:
                        _os_module.kill(old_pid, signal.SIGKILL)
                    except OSError:
                        pass
        except Exception:
            pass  # 进程可能已经不存在
        finally:
            # 无论成功与否，删除旧 PID 文件
            try:
                pid_file.unlink()
            except OSError:
                pass

    # ── 策略 2：重新启动 Trade ──
    # 新进程独立于当前进程（start_new_session / CREATE_NEW_PROCESS_GROUP）
    cmd = [sys.executable, "-m", "trade"] if "trade" in sys.argv[0] or sys.argv[0].endswith("trade") else [sys.executable, sys.argv[0]]
    # 更可靠的启动方式：使用和当前进程相同的 Python，运行 trade package
    # 通过 sys.argv 推断启动方式
    if len(sys.argv) > 0 and "server.py" in sys.argv[0]:
        # 可能是 python server.py 方式启动
        server_py = Path(sys.argv[0]).resolve()
        if server_py.is_file():
            cmd = [sys.executable, str(server_py)]
        else:
            cmd = [sys.executable, "-m", "trade"]  # fallback
    else:
        cmd = [sys.executable, "-m", "trade"]  # 默认用包方式启动

    # 继承原始启动参数（如 --port）
    extra_args = []
    _skip_next = False
    for _i, arg in enumerate(sys.argv[1:], 1):
        if _skip_next:
            _skip_next = False
            continue
        if arg in ("update", "backup", "skills-update", "update-trade"):
            continue  # 子命令不传递
        if arg.startswith("--port") or arg.startswith("--host") or arg == "--no-browser" or arg == "--no-gateway":
            extra_args.append(arg)
            continue
    cmd.extend(extra_args)

    try:
        kwargs = {
            "stdout": _sp.DEVNULL,
            "stderr": _sp.DEVNULL,
        }
        if sys_name == "Windows":
            kwargs["creationflags"] = 0x00000200  # CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        _sp.Popen(cmd, **kwargs)
        print("  ↻ Trade 服务已重新启动")
        return
    except Exception as e:
        print(f"  ⚠ 自动重启失败: {e}")

    # ── 策略 3：fallback — launchd (macOS) / systemd (Linux) ──
    label = "com.trade.assistant"

    if sys_name == "Darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        if plist.exists():
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
                return
            except Exception:
                pass

    if sys_name == "Linux":
        for _cmd in (
            ["systemctl", "--user", "restart", label],
            ["sudo", "systemctl", "restart", label],
        ):
            r = _sp.run(_cmd, capture_output=True, timeout=10)
            if r.returncode == 0:
                print("  ↻ Trade 后台服务已重新启动（systemd）")
                return

    # ── 无法自动重启时打印明确指引 ──
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


def _sync_trade_template(template_src: Path, trade_home: Path) -> None:
    """将 .trade-template/ 中新增的模板文件同步到 Trade 运行时目录。

    仅复制不存在的文件，不覆盖用户已有数据。
    处理 prompts/system.md 植入逻辑（与 install_skills 中的行为一致）。
    """
    if not template_src.is_dir():
        return

    _dest = trade_home / ".trade-template"
    if not _dest.exists():
        # 整个模板目录不存在，全量复制
        shutil.copytree(template_src, _dest, dirs_exist_ok=False)
        for f in _dest.rglob("*"):
            if f.is_file():
                f.chmod(0o644)
    else:
        # 模板目录已存在，仅复制新增的文件
        for item in template_src.rglob("*"):
            rel = item.relative_to(template_src)
            target = _dest / rel
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif item.is_file() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                target.chmod(0o644)

    # 从模板植入 ~/.trade/prompts/system.md（仅当尚未存在时）
    prompts_src = template_src / "prompts" / "system.md"
    prompts_dir = trade_home / "prompts"
    prompts_dst = prompts_dir / "system.md"
    if prompts_src.is_file() and not prompts_dst.is_file():
        prompts_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prompts_src, prompts_dst)
        prompts_dst.chmod(0o644)


def _guess_running_project_dir() -> Path | None:
    """推断当前运行中的 Trade 项目目录。

    通过 server.py 的 __file__ 路径推断（开发环境 / 桌面安装）。
    如果 server.py 在 site-packages 中（pip install 方式），返回 None。
    """
    # 最可靠：通过检查运行中的 server 模块的 __file__ 路径
    # post_install.py 位于 trade/ 包中，向上找项目根
    # 但如果是从 pip install -e 安装的开发版本，这里返回的是安装源目录
    self_dir = Path(__file__).resolve().parent.parent  # post_install.py -> trade/ -> project root
    if (self_dir / "server.py").is_file() and (self_dir / ".git").is_dir():
        return self_dir

    # 尝试通过 sys.modules 寻找已加载的 server 模块
    import sys as _sys
    for _mod_name in ("server", "__main__"):
        _mod = _sys.modules.get(_mod_name)
        if _mod and hasattr(_mod, "__file__") and _mod.__file__:
            _p = Path(_mod.__file__).resolve().parent
            if (_p / "server.py").is_file() and (_p / ".git").is_dir():
                return _p

    return None


def update_trade() -> None:
    """一键更新 Foreign Trade Assistant 系统。

    执行步骤：
      1. git pull（拉取最新代码）
      2. install_skills()（安装新增的 b2b-* skill 目录 + 模板）
      3. update_skills()（从 GitHub 同步 SKILL.md 内容）
      4. pip install（更新包及依赖）
      5. _sync_trade_template()（同步 .trade-template/ 新增模板文件）
      6. 数据库迁移检查
      7. 自动重启 Trade 服务

    用法：trade-update（或 trade update）
    """
    import subprocess

    # 优先使用当前运行 server.py 所在的项目目录（开发环境/桌面安装），
    # 确保更新的是正在运行的代码而非其他安装副本
    _running_dir = _guess_running_project_dir()
    trade_dir = (_running_dir
                 if _running_dir and (_running_dir / ".git").is_dir()
                 else _get_trade_home() / "foreign-trade-assistant")
    if not trade_dir.is_dir():
        print("[update_trade] ERROR: Trade install directory not found.", file=sys.stderr)
        print(f"  Expected: {trade_dir}", file=sys.stderr)
        sys.exit(1)

    ok = True

    # 1. git pull — 拉取最新代码
    print("→ Step 1/6: git pull ...")
    result = subprocess.run(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=str(trade_dir), capture_output=True, text=True,
    )
    if result.returncode != 0:
        err_text = result.stderr.strip()
        print(f"  ⚠ git pull failed: {err_text}")
        if "not something we can merge" in err_text or "uncommitted" in err_text:
            print("  💡 本地代码有修改。尝试自动 stash 后重试...")
            # 自动 stash + pull + pop，降低用户操作门槛
            _stash = subprocess.run(
                ["git", "stash"],
                cwd=str(trade_dir), capture_output=True, text=True,
            )
            if _stash.returncode == 0:
                _pull2 = subprocess.run(
                    ["git", "pull", "--ff-only", "origin", "main"],
                    cwd=str(trade_dir), capture_output=True, text=True,
                )
                if _pull2.returncode == 0:
                    print(f"  ✓ git pull (after stash) — {_pull2.stdout.strip().split(chr(10))[-1] if _pull2.stdout.strip() else 'OK'}")
                    # 尝试恢复用户本地修改
                    _pop = subprocess.run(
                        ["git", "stash", "pop"],
                        cwd=str(trade_dir), capture_output=True, text=True,
                    )
                    if _pop.returncode == 0:
                        print("  ✓ 本地修改已恢复")
                    else:
                        print("  ⚠ 本地修改合并冲突，已保留在 git stash 中")
                        print("    恢复: cd ~/.trade/foreign-trade-assistant && git stash pop")
                else:
                    print(f"  ⚠ git pull failed after stash: {_pull2.stderr.strip()}")
                    ok = False
            else:
                print(f"  ⚠ git stash 也失败了: {_stash.stderr.strip()}")
                ok = False
        else:
            print("  (继续后续步骤...数据不受影响)")
            ok = False
    else:
        print(f"  ✓ {result.stdout.strip().split(chr(10))[-1] if result.stdout.strip() else 'Already up-to-date.'}")

    # 2. install_skills — 安装新增 b2b-* skill 目录到 ~/.hermes/skills/
    print("→ Step 2/6: install skills (新增 skill 目录) ...")
    try:
        install_skills()
    except SystemExit:
        ok = False

    # 3. update_skills — 从 GitHub 同步每个 skill 的 SKILL.md 内容
    print("→ Step 3/6: update skills (同步 SKILL.md) ...")
    try:
        update_skills()
    except SystemExit:
        ok = False

    # 4. pip install — 更新包及依赖（包含依赖以确保新版本需求被满足）
    print("→ Step 4/6: pip install ...")
    pip_args = [sys.executable, "-m", "pip", "install", "-e", str(trade_dir)]
    result = subprocess.run(pip_args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ pip install failed: {result.stderr.strip()}")
        ok = False
    else:
        print("  ✓ Package updated")

    # 5. 同步 .trade-template/ 新增模板文件
    print("→ Step 5/6: template sync ...")
    try:
        # git pull 后的项目根目录下的 .trade-template/
        template_src = trade_dir / ".trade-template"
        trade_home = _get_trade_home()
        trade_home.mkdir(parents=True, exist_ok=True)
        _sync_trade_template(template_src, trade_home)
        print("  ✓ Templates synced")
    except Exception as e:
        print(f"  ⚠ Template sync failed: {e}")
        # 模板同步失败不影响其他步骤
        pass

    # 6. db migration (幂等操作)
    print("→ Step 6/6: database check ...")
    try:
        from trade.database import init_db
        db_path = init_db()
        print(f"  ✓ Database OK ({db_path})")
    except Exception as e:
        print(f"  ⚠ Database check failed: {e}")
        ok = False

    if ok:
        print("\n✅ Trade update complete.")
        # 延迟重启：给 HTTP 请求留出时间返回响应，避免 ERR_EMPTY_RESPONSE
        import threading as _threading
        _threading.Thread(target=lambda: (__import__("time").sleep(1.5), _restart_trade_service()), daemon=True).start()
    else:
        print("\n⚠️  Trade update completed with warnings. Check the output above.")


def backup_trade(output_dir: str | None = None) -> str:
    """备份 Trade 系统数据为 tar.gz 压缩包。

    包含：
      - ~/.trade/data/trade.db（SQLite 数据库）
      - ~/.trade/companies/{slug}/（公司数据）
      - ~/.trade/prompts/（系统 prompts）
      - ~/.hermes/memories/（Hermes 记忆）
      - ~/.hermes/skills/b2b-*/（B2B skills）

    Args:
        output_dir: 输出目录（默认桌面）

    Returns:
        生成的 tar.gz 文件路径

    用法：trade-backup [output_dir]（或 trade backup）
    """
    import datetime
    import tarfile

    if output_dir is None:
        # 未指定输出目录时默认使用桌面
        desktop = Path.home() / "Desktop"
        if not desktop.is_dir():
            # 英文桌面路径不存在时尝试中文桌面路径
            desktop = Path.home() / "桌面"
        if not desktop.is_dir():
            # 两个桌面路径都不存在时回退到家目录
            desktop = Path.home()
        output_dir = str(desktop)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"trade-backup-{timestamp}.tar.gz"
    out_path = Path(output_dir) / filename

    trade_home = _get_trade_home()
    hermes_home = _get_hermes_home()

    # 需要打包的路径列表
    sources: list[tuple[Path, str]] = []  # (absolute_path, arcname_in_tar)

    # SQLite 数据库文件
    db_path = trade_home / "data" / "trade.db"
    if db_path.is_file():
        sources.append((db_path, ".trade/data/trade.db"))

    # 公司数据目录（每个公司一个子目录）
    companies_dir = trade_home / "companies"
    if companies_dir.is_dir():
        # 遍历所有公司目录，递归添加所有文件
        for company_dir in companies_dir.iterdir():
            if company_dir.is_dir():
                for f in company_dir.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(trade_home))
                        sources.append((f, f".trade/{rel}"))

    # prompts 目录（系统提示词文件）
    prompts_dir = trade_home / "prompts"
    if prompts_dir.is_dir():
        for f in prompts_dir.rglob("*"):
            if f.is_file():
                sources.append((f, f".trade/{f.relative_to(trade_home)}"))

    # Hermes 记忆文件
    memories_dir = hermes_home / "memories"
    if memories_dir.is_dir():
        for f in memories_dir.rglob("*"):
            # 只备份 markdown、json、txt 格式的记忆文件
            if f.is_file() and f.suffix in (".md", ".json", ".txt"):
                sources.append((f, f".hermes/memories/{f.relative_to(memories_dir)}"))

    # B2B skills 定义
    skills_dir = hermes_home / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            # 只备份 b2b 前缀的 skill 的 SKILL.md 文件
            if skill_dir.is_dir() and skill_dir.name.startswith("b2b-"):
                skill_md = skill_dir / "SKILL.md"
                if skill_md.is_file():
                    sources.append((skill_md, f".hermes/skills/{skill_dir.name}/SKILL.md"))

    if not sources:
        # 没有找到任何可备份的数据
        print("[backup] WARNING: No data found to backup.")
        sys.exit(1)

    print(f"[backup] Packaging {len(sources)} files ...")
    with tarfile.open(out_path, "w:gz") as tar:
        for abs_path, arcname in sources:
            tar.add(str(abs_path), arcname=arcname)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"[backup] Done: {out_path} ({size_mb:.1f} MB)")
    return str(out_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trade Skills Manager")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("install", help="Install skills from local package")
    sub.add_parser("update", help="Update skills from GitHub")
    p_up = sub.add_parser("update-trade", help="Update entire Trade system")
    p_backup = sub.add_parser("backup", help="Backup Trade data")
    p_backup.add_argument("--output", "-o", default=None, help="Output directory (default: Desktop)")

    args = parser.parse_args()
    if args.command == "update":
        # 从 GitHub 更新 skills
        update_skills()
    elif args.command == "update-trade":
        # 一键更新整个 Trade 系统
        update_trade()
    elif args.command == "backup":
        # 备份 Trade 数据到 tar.gz
        backup_trade(args.output)
    else:
        # 默认：从本地包安装 skills
        install_skills()
