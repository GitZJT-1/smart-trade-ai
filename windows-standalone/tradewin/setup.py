"""
TradeWin — 环境自举模块。

负责在首次运行时自动检测并安装 Hermes Agent，创建 Trade 所需的
所有目录、配置文件和数据文件，实现真正的单文件部署。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

_LOCAL = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path(_LOCAL) / "hermes")))
_TRADE_HOME = Path(os.environ.get("TRADE_HOME", str(Path(_LOCAL) / "trade")))


# ── 检测函数 ──────────────────────────────────────────────────────────────

def is_hermes_installed() -> bool:
    """检查 Hermes Agent 是否已安装（CLI 可执行 + skills 目录存在）。"""
    # 检查 hermes CLI 是否在 PATH 中
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        return True
    # 检查 pip 中是否已安装 hermes-agent 包
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "hermes-agent"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_trade_initialized() -> bool:
    """检查 Trade 数据库是否已初始化（首次运行标志）。"""
    db_path = _TRADE_HOME / "data" / "trade.db"
    return db_path.is_file()


def is_api_key_configured() -> bool:
    """检查 LLM API key 是否已配置。"""
    env_file = _HERMES_HOME / ".env"
    if not env_file.is_file():
        return False
    content = env_file.read_text(encoding="utf-8")
    # 检查至少有一个 API key 环境变量被设置
    for key_env in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MINIMAX_API_KEY",
                    "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY"):
        if key_env in content and "your-" not in content.lower():
            return True
    return False


# ── 安装函数 ──────────────────────────────────────────────────────────────

def install_hermes(progress_callback=None) -> bool:
    """通过 pip 安装 Hermes Agent。

    Args:
        progress_callback: 可选的进度回调 progress_callback(msg: str)

    Returns:
        True 表示安装成功
    """
    if progress_callback:
        progress_callback("正在安装 Hermes Agent（AI 引擎）...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "hermes-agent"],
            capture_output=True, text=True, timeout=300,  # 5 分钟超时
        )
        if result.returncode != 0:
            if progress_callback:
                progress_callback(f"Hermes 安装失败: {result.stderr[-200:]}")
            return False

        if progress_callback:
            progress_callback("Hermes Agent 安装完成")

        # Hermes 安装后不会自动创建目录结构，首次运行 hermes CLI 会创建
        # 但我们需要手动触发
        _HERMES_HOME.mkdir(parents=True, exist_ok=True)
        (_HERMES_HOME / "skills").mkdir(parents=True, exist_ok=True)
        (_HERMES_HOME / "memories").mkdir(parents=True, exist_ok=True)
        (_HERMES_HOME / "cron").mkdir(parents=True, exist_ok=True)

        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"安装异常: {e}")
        return False


def install_trade_skills(progress_callback=None) -> bool:
    """安装 B2B skills 到 Hermes skills 目录。

    从项目自带的 skills/ 目录复制所有 b2b-*/SKILL.md。
    """
    if progress_callback:
        progress_callback("正在安装 Trade 技能包...")

    try:
        from trade.post_install.skills import install_skills as _do_install
        _do_install(progress_callback=progress_callback)
        return True
    except SystemExit as e:
        if progress_callback:
            progress_callback(f"Skill 安装退出 (code={e.code})")
        return e.code == 0
    except Exception as e:
        if progress_callback:
            progress_callback(f"Skill 安装失败: {e}")
        return False


def init_trade_database(progress_callback=None) -> bool:
    """初始化 Trade 数据库 + 迁移。"""
    if progress_callback:
        progress_callback("正在初始化数据库...")

    try:
        _TRADE_HOME.mkdir(parents=True, exist_ok=True)
        from trade.database import init_db
        db_path = init_db()
        if progress_callback:
            progress_callback(f"数据库就绪 ({db_path})")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"数据库初始化失败: {e}")
        return False


# ── 配置写入 ──────────────────────────────────────────────────────────────

def write_hermes_env(provider: str, api_key: str, tavily_key: str = "") -> bool:
    """写入 ~/.hermes/.env 文件（LLM API key + Tavily API key）。

    Args:
        provider: LLM 提供商名称（openai/anthropic/minimax/deepseek/moonshot）
        api_key: API 密钥
        tavily_key: Tavily 搜索 API 密钥（可选）

    Returns:
        True 表示写入成功
    """
    _HERMES_HOME.mkdir(parents=True, exist_ok=True)
    env_file = _HERMES_HOME / ".env"

    # API key 环境变量名映射
    key_env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
    }

    key_env = key_env_map.get(provider, f"{provider.upper()}_API_KEY")

    lines = []
    lines.append("# TradeWin — Hermes 环境配置")
    lines.append("# 生成时间: 首次运行向导")
    lines.append(f"{key_env}={api_key}")
    if tavily_key:
        lines.append(f"TAVILY_API_KEY={tavily_key}")
    lines.append("")

    try:
        env_file.write_text("\n".join(lines), encoding="utf-8")
        # 设置文件权限（仅所有者可读写）
        if os.name != "nt":
            env_file.chmod(0o600)
        return True
    except Exception:
        return False


def write_hermes_config(provider: str, model: str = "") -> bool:
    """写入 ~/.hermes/config.yaml（LLM 提供商 + 默认模型）。

    Args:
        provider: LLM 提供商名称
        model: 默认模型名称（为空则使用 Hermes 默认值）
    """
    _HERMES_HOME.mkdir(parents=True, exist_ok=True)
    config_file = _HERMES_HOME / "config.yaml"

    # 各提供商的默认模型（保守选择，避免使用可能下线的模型名）
    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-latest",
        "minimax": "MiniMax-M3",
        "deepseek": "deepseek-chat",
        "moonshot": "moonshot-v1-auto",
    }

    chosen_model = model or default_models.get(provider, "gpt-4o")

    import yaml
    config = {
        "model": f"{provider}:{chosen_model}",
        "tools": ["read_file", "list_dir", "web_search", "browser_navigate",
                   "write_file", "database", "memory_recall", "memory_remember"],
        "yolo_mode": True,
        "streaming": True,
    }

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception:
        return False


def get_available_providers() -> list[dict]:
    """获取可用的 LLM 提供商列表（名称 + 描述 + 是否需要 API key）。

    即使 Hermes 未安装，我们也返回内置列表，因为用户要先选择才能安装。
    """
    return [
        {
            "id": "openai",
            "name": "OpenAI",
            "description": "GPT-4o — 综合能力最强",
            "key_name": "OPENAI_API_KEY",
            "key_url": "https://platform.openai.com/api-keys",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        },
        {
            "id": "anthropic",
            "name": "Anthropic Claude",
            "description": "Claude — 长文本分析最强",
            "key_name": "ANTHROPIC_API_KEY",
            "key_url": "https://console.anthropic.com/keys",
            "models": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
        },
        {
            "id": "minimax",
            "name": "MiniMax",
            "description": "M3 — 中文外贸场景性价比最高",
            "key_name": "MINIMAX_API_KEY",
            "key_url": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
            "models": ["MiniMax-M3", "MiniMax-M2"],
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "description": "V4 Flash — 性价比最高，外贸场景首选",
            "key_name": "DEEPSEEK_API_KEY",
            "key_url": "https://platform.deepseek.com/api_keys",
            "models": ["deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
        },
        {
            "id": "moonshot",
            "name": "Moonshot",
            "description": "Kimi — 中文理解优秀",
            "key_name": "MOONSHOT_API_KEY",
            "key_url": "https://platform.moonshot.cn/console/api-keys",
            "models": ["moonshot-v1-auto", "moonshot-v1-8k"],
        },
    ]
