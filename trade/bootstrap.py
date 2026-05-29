"""
Trade AI Assistant — 启动引导模块。

负责：日志过滤、sys.path 调整、子命令分发、Hermes 版本检查、
.env 加载、YOLO 模式设置、Skills 同步。
"""

import hashlib
import logging as _logging
import os
import shutil
import sys
import warnings as _warnings
from pathlib import Path


# ── 日志噪声过滤 ────────────────────────────────────────────────────────────
# 在任何 Hermes import 之前安装日志过滤器，
# 确保 Hermes 启动时的可选工具缺失警告被正确屏蔽
class _ToolImportNoiseFilter(_logging.Filter):
    """过滤 Hermes 启动时无关的可选工具缺失警告。"""
    _NOISE = ("Could not import tool module", "No module named")
    def filter(self, record: _logging.LogRecord) -> bool:
        return not any(p in record.getMessage() for p in self._NOISE)


_logging.getLogger().addFilter(_ToolImportNoiseFilter())
_warnings.filterwarnings("ignore", message=r".*Could not import tool module.*")
_warnings.filterwarnings("ignore", message=r".*No module named.*")


# ── sys.path 调整：Trade 包优先于 Hermes ──────────────────────────────────
# Hermes 也有 `trade/` 包；我们的 `trade/` 必须优先。
# NOTE: 当 hermes-agent 作为独立 pip 包发布后，此块可移除。
def _adjust_sys_path():
    _trade_root = str(Path(__file__).resolve().parent.parent)
    if _trade_root not in sys.path:
        sys.path.insert(0, _trade_root)

    # Hermes 源码路径优先级：
    # 1. HERMES_HOME 环境变量
    # 2. ~/.hermes/hermes-agent/（pip install 的源码目录）
    # 3. 与 Trade 平级的 trade_ai_assistant 开发目录
    _hermes_checkout = os.environ.get("HERMES_HOME", "").strip()
    if not _hermes_checkout:
        _default_hermes = Path.home() / ".hermes" / "hermes-agent"
        if _default_hermes.is_dir():
            _hermes_checkout = str(_default_hermes)
    if not _hermes_checkout:
        _dev_hermes = str(Path(__file__).resolve().parent.parent.parent / "trade_ai_assistant")
        if Path(_dev_hermes).is_dir():
            _hermes_checkout = _dev_hermes

    if _hermes_checkout and _hermes_checkout not in sys.path:
        # Hermes 放在第 1 位，Trade 仍在第 0 位（避免 trade/ 包名冲突）
        sys.path.insert(1, _hermes_checkout)


# ── 子命令分发 ────────────────────────────────────────────────────────────
_MIN_HERMES_VERSION = "0.13.0"
_MAX_HERMES_VERSION = "0.16.0"  # exclusive upper bound: bumped 2026-05-29 for v0.15.0 compatibility


def dispatch_subcommands() -> bool:
    """处理子命令（update/backup/skills-update），无需启动服务器。

    Returns True 表示已处理子命令并应退出进程。
    """
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("update", "backup", "skills-update"):
        return False

    if cmd == "update":
        from trade.post_install import update_trade
        update_trade()
    elif cmd == "backup":
        from trade.post_install import backup_trade
        print(backup_trade())
    else:  # skills-update
        from trade.post_install import update_skills
        update_skills()
    return True


# ── Hermes 版本检查 ──────────────────────────────────────────────────────


def check_hermes_version() -> bool:
    """验证已安装的 Hermes 版本与当前 Trade 版本兼容。

    使用 packaging.version 进行 PEP 440 版本比较。
    Returns True 表示兼容，False 表示不兼容。
    """
    from packaging.version import Version

    try:
        from hermes_cli import __version__ as _hv
    except ImportError:
        print("  ✗ Cannot import Hermes. Is hermes-agent installed?")
        print("    Install: pip install hermes-agent")
        return False

    current = Version(_hv)
    min_v = Version(_MIN_HERMES_VERSION)
    max_v = Version(_MAX_HERMES_VERSION)

    if not (min_v <= current < max_v):
        print(f"  ✗ Hermes version {_hv} is not compatible with this release.")
        print(f"    Foreign Trade Assistant requires hermes-agent >={_MIN_HERMES_VERSION},<{_MAX_HERMES_VERSION}.")
        print(f"    Installed: {_hv}")
        print(f"    Run: pip install 'hermes-agent>={_MIN_HERMES_VERSION},<{_MAX_HERMES_VERSION}'")
        return False

    print(f"  ✓ Hermes {_hv} (compatible: >={_MIN_HERMES_VERSION},<{_MAX_HERMES_VERSION})")
    return True


# ── .env 加载 + YOLO 模式 ────────────────────────────────────────────────


def load_env_and_set_yolo():
    """加载 Hermes .env 并开启 YOLO 模式（跳过工具审批）。"""
    from hermes_cli.env_loader import load_hermes_dotenv
    from hermes_constants import get_hermes_home

    load_hermes_dotenv(hermes_home=get_hermes_home())
    os.environ["HERMES_YOLO_MODE"] = "true"


# ── Skills 同步 ──────────────────────────────────────────────────────────


def sync_b2b_skills():
    """启动时从 GitHub 拉取最新 B2B skills 到 Hermes。

    每次启动都会检查并更新。如果 GitHub 不可达，降级为本地 hash 比对同步。
    """
    from hermes_constants import get_hermes_home

    from trade.post_install import update_skills

    try:
        update_skills()
    except Exception as e:
        print(f"  GitHub skills update failed ({e}), falling back to local sync")

        _project_root = Path(__file__).resolve().parent.parent
        _project_skills = _project_root / "skills"
        if not _project_skills.is_dir():
            return

        _hermes_skills = get_hermes_home() / "skills"
        _hermes_skills.mkdir(parents=True, exist_ok=True)

        synced = 0
        for skill_dir in sorted(_project_skills.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("b2b-"):
                continue
            src = skill_dir / "SKILL.md"
            if not src.is_file():
                continue
            dst_dir = _hermes_skills / skill_dir.name
            dst = dst_dir / "SKILL.md"
            src_hash = hashlib.sha256(src.read_bytes()).hexdigest()
            if dst.is_file():
                dst_hash = hashlib.sha256(dst.read_bytes()).hexdigest()
                if src_hash == dst_hash:
                    continue
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            synced += 1
            print(f"  ↻ Updated skill: {skill_dir.name}")

        if synced > 0:
            print(f"  Skills synced: {synced} updated")
        else:
            print("  Skills: up-to-date")


# ── 一键 setup ───────────────────────────────────────────────────────────


def setup():
    """执行 Trade 启动所需的所有引导步骤。

    调用顺序：
    1. sys.path 调整
    2. 子命令分发（如果是子命令则直接 exit）
    3. Hermes 版本检查
    4. .env 加载 + YOLO 设置
    5. Skills 同步
    """
    _adjust_sys_path()

    if dispatch_subcommands():
        sys.exit(0)

    if not check_hermes_version():
        sys.exit(1)

    load_env_and_set_yolo()
    sync_b2b_skills()
