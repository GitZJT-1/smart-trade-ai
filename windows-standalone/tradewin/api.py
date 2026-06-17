"""
TradeWin — 本地 FastAPI HTTP 客户端。

封装所有与 localhost:9119 的 API 通信，统一处理 session token、company header。
使用标准库 urllib（无 httpx/requests 依赖，减小 PyInstaller 打包体积）。
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error

_BASE = "http://127.0.0.1:9119"
_session_token: str = ""  # 首次 /api/status 时自动获取
_company_id: str = ""     # 当前选中的公司 ID


def set_company(cid: str) -> None:
    """切换当前公司（所有后续请求携带 X-Company-ID header）。"""
    global _company_id
    _company_id = cid


def _get(path: str) -> dict | None:
    """GET 请求，返回 JSON dict 或 None（网络错误时）。"""
    url = f"{_BASE}{path}"
    req = urllib.request.Request(url)
    if _session_token:
        req.add_header("X-Hermes-Session-Token", _session_token)
    if _company_id:
        req.add_header("X-Company-ID", _company_id)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _post(path: str, body: dict | None = None) -> dict | None:
    """POST 请求，返回 JSON dict 或 None。"""
    url = f"{_BASE}{path}"
    data = json.dumps(body).encode() if body else b"{}"
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if _session_token:
        req.add_header("X-Hermes-Session-Token", _session_token)
    if _company_id:
        req.add_header("X-Company-ID", _company_id)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


# ── 公开 API 函数 ──────────────────────────────────────────────────────────

def init_session() -> dict | None:
    """从 /trade HTML 页面提取 session token。

    Trade 服务在返回的 HTML 中注入 __TRADE_SESSION_TOKEN__ 占位符。
    解析该 token 后用于所有后续 API 请求的身份认证。
    """
    global _session_token
    url = f"{_BASE}/trade"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode()
            import re
            m = re.search(r"__TRADE_SESSION_TOKEN__\s*=\s*'([^']+)'", html)
            if m:
                _session_token = m.group(1)
                return {"ok": True}
    except Exception:
        pass
    return None


def get_status() -> dict | None:
    """GET /api/status — 版本检查 + 健康状态（含 started_at 重启检测时间戳）。"""
    return _get("/api/status")


def list_companies() -> list[dict]:
    """GET /api/trade/companies — 公司列表（脱敏版：仅 id/name/slug/is_active）。"""
    r = _get("/api/trade/companies")
    if r and isinstance(r, list):
        return r
    return []


def create_company(name: str) -> dict | None:
    """POST /api/trade/companies — 创建公司（自动创建桌面工作目录 + 文档库）。"""
    return _post("/api/trade/companies", {"name": name})


def list_customers() -> list[dict]:
    """GET /api/trade/customers — 客户列表。"""
    r = _get("/api/trade/customers")
    if r and isinstance(r, list):
        return r
    return []


def list_libraries() -> list[dict]:
    """GET /api/trade/libraries — 文档库列表。"""
    r = _get("/api/trade/libraries")
    if r and isinstance(r, list):
        return r
    return []


def send_chat(query: str, library_id: int | None = None) -> dict | None:
    """POST /api/trade/chat — 同步聊天（阻塞等待完整响应，最多 600s）。"""
    body = {"query": query}
    if library_id:
        body["library_id"] = library_id
    return _post("/api/trade/chat", body)


def stream_chat(query: str, on_event, library_id: int | None = None) -> None:
    """POST /api/trade/chat/stream — SSE 流式聊天。

    SSE 事件格式:
      event: tool_start / tool_complete / thinking / response / error / done
      data: { JSON payload }

    Args:
        query: 用户问题
        on_event: 回调函数 on_event(event_type: str, data: dict)
        library_id: 可选，指定文档库 ID
    """
    import urllib.request as _ur

    body = {"query": query}
    if library_id:
        body["library_id"] = library_id
    data = json.dumps(body).encode()

    url = f"{_BASE}/api/trade/chat/stream"
    req = _ur.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    if _session_token:
        req.add_header("X-Hermes-Session-Token", _session_token)
    if _company_id:
        req.add_header("X-Company-ID", _company_id)

    try:
        with _ur.urlopen(req, timeout=600) as resp:  # 10分钟超时（长文档分析）
            buf = ""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buf += chunk.decode()
                # SSE 消息以 \n\n 分隔
                while "\n\n" in buf:
                    event_str, buf = buf.split("\n\n", 1)
                    etype = ""
                    for line in event_str.split("\n"):
                        if line.startswith("event: "):
                            etype = line[7:]
                        elif line.startswith("data: "):
                            try:
                                edata = json.loads(line[6:])
                                on_event(etype, edata)
                            except json.JSONDecodeError:
                                pass
    except Exception as e:
        on_event("error", {"message": str(e)})


def get_license_status() -> dict | None:
    """GET /api/trade/license/status — 许可证状态（试用/激活/到期）。"""
    return _get("/api/trade/license/status")


def activate_license(code: str) -> dict | None:
    """POST /api/trade/license/activate — 激活许可证。"""
    return _post("/api/trade/license/activate", {"code": code})


def system_update() -> dict | None:
    """POST /api/trade/system/update — 一键更新系统（git pull + pip install + 重启）。"""
    return _post("/api/trade/system/update")


def system_restart() -> dict | None:
    """POST /api/trade/system/restart — 重启 Trade 服务。"""
    return _post("/api/trade/system/restart")
