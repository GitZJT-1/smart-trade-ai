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

# ── 非对称签名密钥 ──────────────────────────────────────────────────────

# Ed25519 公钥 — 用于验证激活码签名。私钥由作者持有，用户端无法生成合法激活码。
_PUBLIC_KEY_BYTES = bytes.fromhex(
    "5af8d2a6356dd8c893b050ae111dfd76ed8f71c549f71b3bf645227e56126a9b"
)


def _load_private_key():
    """加载 Ed25519 私钥（仅作者生成激活码时需要）。"""
    from cryptography.hazmat.primitives import serialization

    priv_pem = os.environ.get("TRADE_LICENSE_PRIVATE_KEY", "")
    if not priv_pem:
        priv_file = Path.home() / ".hermes" / "license_private_key.pem"
        if priv_file.is_file():
            priv_pem = priv_file.read_text(encoding="utf-8")
    if priv_pem:
        return serialization.load_pem_private_key(priv_pem.encode(), password=None)
    return None

_TRIAL_DAYS = 30


def _machine_id() -> str:
    """获取本机唯一硬件标识符。

    macOS → IOPlatformUUID (稳定，重装系统前不变)
    Linux   → /etc/machine-id
    Windows → 注册表 MachineGuid
    其他平台 → hostname (fallback)
    """
    import platform as _plat
    import subprocess as _sp

    sys_name = _plat.system()
    if sys_name == "Darwin":
        try:
            result = _sp.run(
                ["ioreg", "-d2", "-c", "IOPlatformExpertDevice"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    uuid = line.strip().split('"')[-2]
                    return f"mac:{uuid}"
        except Exception:
            pass

    elif sys_name == "Linux":
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                mid = Path(path).read_text().strip()
                if mid:
                    return f"linux:{mid}"
            except Exception:
                continue

    elif sys_name == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if guid:
                return f"win:{guid}"
        except Exception:
            pass

    return f"host:{_plat.node()}"

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


def _make_request_code() -> str:
    """生成本机申请码: TRADE-REQ-XXXX-XXXX（基于机器码哈希前 8 位）。"""
    mid = _machine_id()
    h = hashlib.sha256(mid.encode()).hexdigest()[:8].upper()
    return f"TRADE-REQ-{h[:4]}-{h[4:8]}"


def status(company_id: int | None = None) -> dict:
    """返回许可证状态，供前端展示。到期时自动包含 request_code。"""
    data = _get_license_data(company_id)
    now = datetime.now(UTC)

    result: dict = {
        "days_remaining": days_remaining(company_id),
        "activated": data.get("activated", False),
        "expires_at": data.get("expires_at"),
        "trial_used": 0,
        "trial_total": _TRIAL_DAYS,
        "request_code": "",
    }

    if "first_launch_at" in data:
        first = datetime.fromisoformat(data["first_launch_at"])
        result["trial_used"] = min((now - first).days, _TRIAL_DAYS)

    if not result["activated"] and result["days_remaining"] <= 0:
        result["status"] = "expired"
        result["request_code"] = _make_request_code()
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

    # 验证机器码：本机哈希的前 8 位必须匹配激活码中的哈希
    local_hash = hashlib.sha256(_machine_id().encode()).hexdigest()[:8].upper()
    if not hmac.compare_digest(local_hash, decoded["machine_hash"]):
        return False, "此激活码不适用于本机。请在本机上生成申请码后联系作者。"

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


def _encode_activation_code(request_code: str, expires_at: str) -> str:
    """根据申请码和到期日期生成激活码。

    编码格式: TRADE-{base64url(日期 + 机器码哈希 + Ed25519签名)}
    内部 payload = 8 bytes 日期 + 8 bytes 机器码哈希 → Ed25519 签名 64 bytes。
    激活码 ~110 字符。

    Args:
        request_code: 用户发送的申请码 (TRADE-REQ-XXXX-XXXX)
        expires_at: ISO 日期字符串，如 "2027-06-01"
    """
    import base64

    private_key = _load_private_key()
    if private_key is None:
        raise ValueError(
            "私钥未找到。请将私钥保存为 ~/.hermes/license_private_key.pem "
            "或设置 TRADE_LICENSE_PRIVATE_KEY 环境变量。"
        )

    req_hash = request_code.replace("TRADE-REQ-", "").replace("-", "").upper()
    date_str = expires_at[:10].replace("-", "")  # YYYYMMDD

    # payload: 日期(8) + 机器码哈希(8) = 16 bytes ASCII hex
    payload = (date_str + req_hash).encode()

    # Ed25519 签名
    sig = private_key.sign(payload)

    # 打包: 日期 + 机器码哈希 + 签名 → base64url
    combined = date_str.encode() + req_hash.encode() + sig
    b64 = base64.urlsafe_b64encode(combined).decode().rstrip("=")
    return f"TRADE-{b64}"


def _decode_activation_code(code: str) -> dict:
    """解码激活码，返回 {expires_at: str, machine_hash: str}。

    激活码格式: TRADE-{base64url(日期+机器码哈希+Ed25519签名)}
    """
    import base64
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.exceptions import InvalidSignature

    # 只去掉前缀 "TRADE-"，保留 base64url 中的 "-" 字符
    b64 = code
    if b64.startswith("TRADE-"):
        b64 = b64[6:]
    # 补回 base64 padding
    b64 += "=" * (-len(b64) % 4)
    decoded = base64.urlsafe_b64decode(b64)

    if len(decoded) < 80:
        raise ValueError(f"Invalid code: expected >= 80 bytes, got {len(decoded)}")

    date_part = decoded[:8].decode()
    req_hash = decoded[8:16].decode()
    sig = decoded[16:80]

    # 验证 Ed25519 签名
    payload = date_part.encode() + req_hash.encode()
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(_PUBLIC_KEY_BYTES)
    try:
        public_key.verify(sig, payload)
    except InvalidSignature:
        raise ValueError("Invalid activation code signature")

    # 解码日期
    expires_at = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"

    return {"expires_at": expires_at, "machine_hash": req_hash}


# ── CLI ────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trade License Manager")
    sub = parser.add_subparsers(dest="cmd")
    gen = sub.add_parser("generate", help="生成激活码")
    gen.add_argument("request_code", help="用户申请码 (TRADE-REQ-XXXX-XXXX-XXXX)")
    gen.add_argument("date", help="到期日期 (YYYY-MM-DD)")
    sub.add_parser("generate-secret", help="随机生成 TRADE_LICENSE_SECRET")
    sub.add_parser("status", help="查看当前许可证状态")

    args = parser.parse_args()

    if args.cmd == "generate":
        code = _encode_activation_code(args.request_code, args.date)
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
