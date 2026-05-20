"""
许可证管理 — 试用期 + 年度激活。

首次使用起 30 天免费试用，到期后需激活码继续使用。
激活码有效期通常为一年。

环境变量：
  TRADE_LICENSE_SECRET — (必填) 激活码 HMAC 签名密钥。未设置时生成和验证激活码的功能不可用。
                        运行 `python -m trade.license generate-secret` 随机生成。

CLI 工具: python -m trade.license --generate YYYY-MM-DD
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path

# ── 激活码 secret ────────────────────────────────────────────────────────────

_SECRET = os.environ.get("TRADE_LICENSE_SECRET", "").encode()
if not _SECRET:
    _SECRET = b""  # 未设置则不提供激活码签名；generate 命令会报错

_TRIAL_DAYS = 30

# 暴力破解限流：内存计数器，记录最近 60 秒内的失败尝试次数
_MAX_ACTIVATE_ATTEMPTS = 10  # 每 60 秒最多 10 次激活尝试
_ACTIVATE_ATTEMPTS: list[float] = []  # 时间戳列表


# ── 数据读写 ──────────────────────────────────────────────────────────────────


def _get_license_data(company_id: int | None = None) -> dict:
    """读取 license_data JSON 字段。

    当 company_id 提供时，读取该公司的 license；否则读取第一个激活公司的。
    如果 trade_companies 表不存在则返回空。
    """
    from trade.database import get_connection
    conn = get_connection()
    try:
        if company_id is not None:
            row = conn.execute(
                "SELECT license_data FROM trade_companies WHERE company_id = ?",
                (company_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT license_data FROM trade_companies WHERE is_active = 1 LIMIT 1"
            ).fetchone()
        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return {}
        return {}
    except Exception:
        # 表可能尚未创建（首次启动时）
        return {}
    finally:
        conn.close()


def _save_license_data(data: dict, company_id: int | None = None) -> None:
    """写入 license_data JSON 字段。

    当 company_id 提供时写入该公司，否则写入第一个激活的公司。
    """
    from trade.database import get_connection
    conn = get_connection()
    try:
        payload = json.dumps(data, ensure_ascii=False)
        if company_id is not None:
            conn.execute(
                "UPDATE trade_companies SET license_data = ? WHERE company_id = ?",
                (payload, company_id),
            )
        else:
            conn.execute(
                "UPDATE trade_companies SET license_data = ? WHERE is_active = 1",
                (payload,),
            )
        conn.commit()
    finally:
        conn.close()


# ── 许可证检查 ────────────────────────────────────────────────────────────────


def check_license(company_id: int | None = None) -> tuple[bool, str]:
    """检查许可证状态。

    Args:
        company_id: 要检查的公司 ID。None 时检查第一个激活的公司。

    Returns:
        (is_valid, message): is_valid=True 表示可以继续使用。
        到期时 is_valid=False，message 包含提示信息。
    """
    data = _get_license_data(company_id)

    now = datetime.now(UTC)

    # 首次使用：记录时间
    if "first_launch_at" not in data:
        data["first_launch_at"] = now.isoformat()
        _save_license_data(data, company_id)
        return True, ""

    first = datetime.fromisoformat(data["first_launch_at"])
    days_used = (now - first).days

    # 已激活：检查是否在有效期内
    if data.get("activated") and data.get("expires_at"):
        expires = datetime.fromisoformat(data["expires_at"])
        if now < expires:
            return True, ""
        else:
            return False, "激活码已到期，请联系作者续期：lauroge@gmail.com"

    # 试用期内
    if days_used < _TRIAL_DAYS:
        return True, ""

    # 试用到期
    return False, f"试用期（{_TRIAL_DAYS}天）已到期。请联系 lauroge@gmail.com 获取激活码。"


def days_remaining(company_id: int | None = None) -> int:
    """返回剩余可用天数。已过期返回 0。"""
    data = _get_license_data(company_id)
    now = datetime.now(UTC)

    if data.get("activated") and data.get("expires_at"):
        expires = datetime.fromisoformat(data["expires_at"])
        remaining = (expires - now).days
        return max(0, remaining)

    if "first_launch_at" in data:
        first = datetime.fromisoformat(data["first_launch_at"])
        used = (now - first).days
        return max(0, _TRIAL_DAYS - used)

    return _TRIAL_DAYS


def status(company_id: int | None = None) -> dict:
    """返回许可证状态，供前端展示。"""
    data = _get_license_data(company_id)
    now = datetime.now(UTC)

    result: dict = {
        "days_remaining": days_remaining(company_id),
        "activated": data.get("activated", False),
        "expires_at": data.get("expires_at"),
        "trial_used": 0,
        "trial_total": _TRIAL_DAYS,
    }

    if "first_launch_at" in data:
        first = datetime.fromisoformat(data["first_launch_at"])
        result["trial_used"] = min((now - first).days, _TRIAL_DAYS)

    if not result["activated"] and result["days_remaining"] <= 0:
        result["status"] = "expired"
    elif result["activated"]:
        result["status"] = "active"
    else:
        result["status"] = "trial"

    return result


# ── 激活码验证 ────────────────────────────────────────────────────────────────


def _check_activate_rate_limit() -> bool:
    """检查激活尝试是否超过限流阈值。返回 True 表示允许继续。"""
    global _ACTIVATE_ATTEMPTS
    now = time.time()
    # 清理 60 秒之前的时间戳
    _ACTIVATE_ATTEMPTS = [t for t in _ACTIVATE_ATTEMPTS if now - t < 60]
    if len(_ACTIVATE_ATTEMPTS) >= _MAX_ACTIVATE_ATTEMPTS:
        return False
    _ACTIVATE_ATTEMPTS.append(now)
    return True


def activate(code: str, company_id: int | None = None) -> tuple[bool, str]:
    """验证激活码并激活。

    Args:
        code: 激活码字符串
        company_id: 要激活的公司 ID。None 时激活第一个激活的公司。

    Returns:
        (success, message): success=True 表示激活成功。
    """
    if not _SECRET:
        return False, "服务器未配置许可证签名密钥。请联系管理员设置 TRADE_LICENSE_SECRET。"

    if not _check_activate_rate_limit():
        return False, "激活尝试过于频繁，请 60 秒后重试。"

    if not code or len(code.strip()) < 8:
        return False, "无效的激活码格式"

    code = code.strip().upper()

    # 解码激活码
    try:
        decoded = _decode_activation_code(code)
    except Exception:
        return False, "激活码无效"

    expires_at = decoded["expires_at"]
    now = datetime.now(UTC)

    if now >= datetime.fromisoformat(expires_at):
        return False, f"该激活码已到期（有效期至 {expires_at[:10]}）"

    # 写入激活信息
    data = _get_license_data(company_id)
    data["activated"] = True
    data["code"] = code
    data["expires_at"] = expires_at
    data["activated_at"] = now.isoformat()
    _save_license_data(data, company_id)

    return True, f"激活成功，有效期至 {expires_at[:10]}"


# ── 激活码编解码 ──────────────────────────────────────────────────────────────


def _encode_activation_code(expires_at: str) -> str:
    """根据到期日期生成激活码。

    Args:
        expires_at: ISO 日期字符串，如 "2027-05-19"

    Raises:
        ValueError: TRADE_LICENSE_SECRET 未设置
    """
    if not _SECRET:
        raise ValueError("TRADE_LICENSE_SECRET 环境变量未设置，无法生成激活码。")
    payload = expires_at[:10]  # YYYY-MM-DD
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:8]
    combined = (payload.replace("-", "") + sig).encode()
    b64 = _base64url_encode(combined)
    return f"TRADE-{b64[:4]}-{b64[4:8]}-{b64[8:12]}".upper()


def _decode_activation_code(code: str) -> dict:
    """解码激活码，返回 {expires_at: str}。"""
    core = code.replace("TRADE-", "").replace("-", "").upper()
    decoded = _base64url_decode(core)

    date_part = decoded[:8].decode()
    expires_at = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
    sig_part = decoded[8:].decode()

    # 验证签名
    expected_payload = expires_at.encode()
    expected_sig = hmac.new(_SECRET, expected_payload, hashlib.sha256).hexdigest()[:8]
    if not hmac.compare_digest(sig_part, expected_sig):
        raise ValueError("Invalid activation code signature")

    return {"expires_at": expires_at}


_BASE64URL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _base64url_encode(data: bytes) -> str:
    result = []
    for i in range(0, len(data), 3):
        chunk = data[i:i+3]
        bits = (chunk[0] << 16) | (chunk[1] << 8 if len(chunk) > 1 else 0) | (chunk[2] if len(chunk) > 2 else 0)
        result.append(_BASE64URL_CHARS[(bits >> 18) & 63])
        result.append(_BASE64URL_CHARS[(bits >> 12) & 63])
        result.append(_BASE64URL_CHARS[(bits >> 6) & 63] if len(chunk) > 1 else "=")
        result.append(_BASE64URL_CHARS[bits & 63] if len(chunk) > 2 else "=")
    return "".join(result)


def _base64url_decode(s: str) -> bytes:
    s = s.rstrip("=")
    result = bytearray()
    for i in range(0, len(s), 4):
        chunk = s[i:i+4]
        idx = [_BASE64URL_CHARS.index(c) for c in chunk]
        val = (idx[0] << 18) | (idx[1] << 12)
        result.append((val >> 16) & 0xFF)
        if len(chunk) > 2 and chunk[2] != "=":
            val |= (idx[2] << 6)
            result.append((val >> 8) & 0xFF)
        if len(chunk) > 3 and chunk[3] != "=":
            val |= idx[3]
            result.append(val & 0xFF)
    return bytes(result)


# ── CLI ────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trade License Manager")
    sub = parser.add_subparsers(dest="cmd")
    gen = sub.add_parser("generate", help="生成激活码")
    gen.add_argument("date", help="到期日期 (YYYY-MM-DD)")
    sub.add_parser("generate-secret", help="随机生成 TRADE_LICENSE_SECRET")
    sub.add_parser("status", help="查看当前许可证状态")

    args = parser.parse_args()

    if args.cmd == "generate":
        code = _encode_activation_code(args.date)
        print(f"激活码: {code}")
        print(f"有效期至: {args.date}")
    elif args.cmd == "generate-secret":
        print(f"TRADE_LICENSE_SECRET={secrets.token_urlsafe(32)}")
        print("# 将以上行添加到 ~/.hermes/.env 或 export 到环境中")
    elif args.cmd == "status":
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        s = status()
        print(f"状态: {s['status']}")
        print(f"已激活: {s['activated']}")
        print(f"剩余天数: {s['days_remaining']}")
        if s.get("expires_at"):
            print(f"到期日期: {s['expires_at'][:10]}")
        print(f"试用进度: {s['trial_used']}/{s['trial_total']} 天")
    else:
        parser.print_help()
