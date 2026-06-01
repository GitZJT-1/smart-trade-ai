"""
Trade AI Assistant — AI 聊天 API 路由。

端点：
  POST /chat         — 同步聊天（线程池 + 600s 超时）
  POST /chat/stream  — SSE 流式聊天（asyncio.Queue + 心跳 + 断连取消）
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from trade import chat_memory
from trade import library as library_module
from trade.api.deps import require_company
from trade.api.models import ChatRequest
from trade.helpers import build_query, create_agent

_log = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# ── 简单内存限流（per-process，适合单机部署）──────────────────────────────────
# 60 秒窗口内最多 20 次 chat 请求（含 sync + SSE）
_MAX_CHAT_PER_MINUTE = 20
_WINDOW_SECONDS = 60.0
_chat_timestamps: list[float] = []
_rate_limit_lock = threading.Lock()


def _check_chat_rate_limit() -> bool:
    """检查是否超过 chat 限流阈值。返回 True 表示允许继续。"""
    global _chat_timestamps
    now = time.time()
    # 线程安全：执行器线程和主线程可能同时访问
    with _rate_limit_lock:
        _chat_timestamps = [t for t in _chat_timestamps if now - t < _WINDOW_SECONDS]
        if len(_chat_timestamps) >= _MAX_CHAT_PER_MINUTE:
            return False
        _chat_timestamps.append(now)
        return True

# ── 同步聊天 ──────────────────────────────────────────────────────────────

@router.post("/chat")
async def trade_chat(
    payload: ChatRequest,
    cid: int = Depends(require_company),
):
    """同步聊天。"""
    from trade.license import check_license
    lic_ok, lic_msg = check_license(cid)
    if not lic_ok:
        raise HTTPException(status_code=402, detail=lic_msg)

    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not _check_chat_rate_limit():
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试。")

    full_query, skill_hint = build_query(cid, payload.library_id, query, customer_id=payload.customer_id)

    _MAX_AGENT_RETRIES = 1  # 最多重试 1 次（共 2 次尝试），避免 Token 费用翻倍

    def _call_agent():
        last_error = ""
        for attempt in range(_MAX_AGENT_RETRIES + 1):
            try:
                agent = create_agent(ephemeral_system_prompt=skill_hint)
                result = agent.chat(full_query)
                if result:
                    return result
                if attempt < _MAX_AGENT_RETRIES:
                    _log.warning("Agent returned empty, retry %d/%d", attempt + 1, _MAX_AGENT_RETRIES)
                    time.sleep(2 ** attempt)
                    continue
                return "Agent 返回了空响应。"
            except ImportError:
                return "⚠️ AI Agent 模块未加载。"
            except RuntimeError as e:
                last_error = str(e)
                if attempt < _MAX_AGENT_RETRIES:
                    _log.warning("Agent RuntimeError, retry %d/%d: %s", attempt + 1, _MAX_AGENT_RETRIES, e)
                    time.sleep(2 ** attempt)
                    continue
                return f"⚠️ {e}"
            except Exception:
                last_error = f"Agent call failed (attempt {attempt + 1})"
                _log.exception(last_error)
                if attempt < _MAX_AGENT_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
        return f"⚠️ Agent 调用失败: {last_error}" if last_error else "⚠️ Agent 调用失败，请稍后重试。"

    loop = asyncio.get_running_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(None, _call_agent),
            timeout=600,
        )
    except TimeoutError:
        response = "⏰ Agent 执行时间过长（超过 10 分钟），已自动中止。请简化问题后重试。"

    lib_name = ""
    if payload.library_id:
        lib = library_module.get(payload.library_id, company_id=cid)
        if lib:
            lib_name = lib["name"]

    conv = chat_memory.save_with_context(
        company_id=cid, library_id=payload.library_id, query=query,
        response=response, library_name=lib_name,
    )
    return {"response": response, "conversation": conv}


# ── SSE 流式聊天 ──────────────────────────────────────────────────────────

@router.post("/chat/stream")
async def trade_chat_stream(
    payload: ChatRequest,
    cid: int = Depends(require_company),
):
    """SSE 流式聊天，实时推送 Agent 工具调用进度。

    使用 asyncio.Queue + call_soon_threadsafe 替代 queue.Queue + executor 轮询，
    每条 SSE 连接只占用 1 条线程。客户端断连时通过 CancelledError 取消 agent。
    """
    from trade.license import check_license
    lic_ok, lic_msg = check_license(cid)
    if not lic_ok:
        raise HTTPException(status_code=402, detail=lic_msg)

    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    if not _check_chat_rate_limit():
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后重试。")

    full_query, skill_hint = build_query(cid, payload.library_id, query, customer_id=payload.customer_id)

    loop = asyncio.get_running_loop()
    event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    def _emit_threadsafe(event_type: str, data: dict | None = None):
        """工作线程通过 call_soon_threadsafe 投递到 asyncio queue。

        put_nowait 在队列满时抛出 QueueFull，用 call_soon_threadsafe 回调时不好捕获，
        改为 queue.put_nowait 包装在一次非阻塞 try 中，满则静默丢弃（优先保持 SSE 连接稳定）。
        """
        def _safe_put(ev_type, ev_data):
            try:
                event_queue.put_nowait((ev_type, ev_data))
            except asyncio.QueueFull:
                _log.warning("SSE event queue full, dropping event: %s", ev_type)

        loop.call_soon_threadsafe(_safe_put, event_type, data or {})

    def _tool_start(tc_id, name, args):
        _emit_threadsafe("tool_start", {"tool_call_id": tc_id, "name": name, "args": args})

    def _tool_complete(tc_id, name, args, result):
        preview = ""
        if isinstance(result, str):
            preview = result[:300]
        elif isinstance(result, (list, dict)):
            preview = _json.dumps(result, ensure_ascii=False)[:300]
        _emit_threadsafe("tool_complete", {
            "tool_call_id": tc_id, "name": name, "result_preview": preview,
        })

    _MAX_AGENT_RETRIES = 2

    def _run_agent() -> str | None:
        last_error = ""
        for attempt in range(_MAX_AGENT_RETRIES + 1):
            try:
                if attempt == 0:
                    _emit_threadsafe("thinking", {"message": "正在分析问题..."})
                else:
                    _emit_threadsafe("thinking", {"message": f"正在重试（第 {attempt} 次）..."})
                agent = create_agent(
                    tool_start_callback=_tool_start,
                    tool_complete_callback=_tool_complete,
                    ephemeral_system_prompt=skill_hint,
                )
                start = time.time()
                result = agent.chat(full_query)
                elapsed = time.time() - start

                if not result and attempt < _MAX_AGENT_RETRIES:
                    _log.warning("Agent returned empty in stream, retry %d/%d", attempt + 1, _MAX_AGENT_RETRIES)
                    time.sleep(2 ** attempt)
                    continue

                _emit_threadsafe("response", {
                    "text": result or "Agent 返回了空响应。",
                    "elapsed_sec": round(elapsed, 1),
                })

                lib_name = ""
                if payload.library_id:
                    lib = library_module.get(payload.library_id, company_id=cid)
                    if lib:
                        lib_name = lib["name"]
                try:
                    chat_memory.save_with_context(
                        company_id=cid, library_id=payload.library_id,
                        query=query, response=result or "",
                        library_name=lib_name,
                    )
                except Exception:
                    _log.exception("save_with_context failed in stream")
                return result
            except ImportError:
                _emit_threadsafe("error", {"message": "AI Agent 模块未加载。"})
                return None
            except RuntimeError as e:
                last_error = str(e)
                if attempt < _MAX_AGENT_RETRIES:
                    _log.warning("Agent RuntimeError in stream, retry %d/%d: %s", attempt + 1, _MAX_AGENT_RETRIES, e)
                    time.sleep(2 ** attempt)
                    continue
                _emit_threadsafe("error", {"message": last_error})
                return None
            except Exception:
                last_error = f"Agent stream failed (attempt {attempt + 1})"
                _log.exception(last_error)
                if attempt < _MAX_AGENT_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                _emit_threadsafe("error", {"message": f"⚠️ {last_error}"})
                return None
        _emit_threadsafe("error", {"message": "Agent 重试耗尽，请稍后重试。"})
        return None

    async def _event_stream():
        def _sse(ev_type: str, payload: dict) -> str:
            return f"event: {ev_type}\ndata: {_json.dumps(payload, ensure_ascii=False)}\n\n"

        agent_task = loop.run_in_executor(None, _run_agent)
        try:
            while True:
                try:
                    # 15s 心跳，防止反向代理/nginx 空闲断开
                    ev_type, ev_data = await asyncio.wait_for(event_queue.get(), timeout=15.0)
                except TimeoutError:
                    if agent_task.done():
                        break
                    yield ": ping\n\n"
                    continue

                yield _sse(ev_type, ev_data)
                if ev_type in ("response", "error"):
                    break
        finally:
            # 客户端断连或异常 → 尝试取消 agent 任务
            if not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except (asyncio.CancelledError, Exception):
                    pass
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
