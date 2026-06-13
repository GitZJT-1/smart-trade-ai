"""
许可证管理 — 试用期 + 年度激活。

首次使用起 30 天免费试用，到期后需激活码继续使用。

激活码使用 Ed25519 非对称签名，公钥内置代码，私钥由作者持有。
用户端可用公钥验签但无法生成合法激活码。

CLI:
  python -m trade.license generate <申请码> <到期日期>    # 作者生成激活码
  python -m trade.license status                          # 查看许可证状态
"""

from __future__ import annotations

import base64
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


def _resolve_hermes_home() -> Path:
    """解析 Hermes 根目录（跨平台）。"""
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(local) / "hermes"
    return Path.home() / ".hermes"


def _load_private_key():
    """加载 Ed25519 私钥（仅作者生成激活码时需要）。"""
    from cryptography.hazmat.primitives import serialization

    priv_pem = os.environ.get("TRADE_LICENSE_PRIVATE_KEY", "")
    if not priv_pem:
        _hermes_root = _resolve_hermes_home()
        priv_file = _hermes_root / "license_private_key.pem"
        if priv_file.is_file():
            # 强制 600 权限防止私钥泄露
            if os.name != "nt":
                priv_file.chmod(0o600)
            priv_pem = priv_file.read_text(encoding="utf-8")
    if priv_pem:
        return serialization.load_pem_private_key(priv_pem.encode(), password=None)
    return None

_TRIAL_DAYS = 30


def _machine_id() -> str:
    """获取本机唯一硬件标识符（首次计算后持久化缓存）。

    首次调用时尝试从系统获取最稳定的标识符（macOS IOPlatformUUID 等），
    成功后立即持久化到 license_data 中。后续调用直接返回缓存值，
    避免因运行环境不同（终端 vs launchd vs 后台进程）导致结果不一致。
    """
    # 从持久化缓存读取
    cached = _get_license_data().get("_machine_id")
    if cached:
        return cached

    import platform as _plat
    import subprocess as _sp

    mid = ""
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
                    mid = f"mac:{uuid}"
                    break
        except Exception:
            pass

    elif sys_name == "Linux":
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                mid = Path(path).read_text().strip()
                if mid:
                    mid = f"linux:{mid}"
                    break
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
                mid = f"win:{guid}"
        except Exception:
            pass

    if not mid:
        mid = f"host:{_plat.node()}"

    # 持久化到 license_data，后续调用直接读取
    try:
        data = _get_license_data()
        data["_machine_id"] = mid
        _save_license_data(data)
    except Exception:
        pass  # 持久化失败不影响使用，只是下次仍需重新检测

    return mid

# 暴力破解限流：持久化到 SQLite license_data 中，进程重启不清零
_MAX_ACTIVATE_ATTEMPTS = 10  # 每 60 秒最多 10 次激活尝试


def _get_activate_attempts(company_id: int | None = None) -> list[float]:
    """从 license_data 读取激活尝试时间戳列表。"""
    data = _get_license_data(company_id)
    return data.get("_activate_attempts", [])


def _save_activate_attempts(attempts: list[float], company_id: int | None = None) -> None:
    """将激活尝试时间戳持久化到 license_data。"""
    data = _get_license_data(company_id)
    data["_activate_attempts"] = attempts
    _save_license_data(data, company_id)


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
        try:
            _save_license_data(data, company_id)
        except Exception:
            # 写入失败（权限不足/磁盘满等）→ 不应静默通过，否则每次启动都重置试用
            return False, "License 状态持久化失败，请检查 ~/.trade/ 目录权限"
        return True, ""

    first = datetime.fromisoformat(data["first_launch_at"])
    days_used = (now - first).days

    # 已激活：验签 + 检查是否在有效期内
    if data.get("activated") and data.get("expires_at"):
        if not _verify_license(data):
            # 签名无效 → license_data 被篡改，要求重新激活
            return False, "许可证数据异常，请使用激活码重新激活。"
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

    # 未激活时始终返回申请码，方便用户在试用期内提前申请激活
    if not result["activated"]:
        result["request_code"] = _make_request_code()

    if not result["activated"] and result["days_remaining"] <= 0:
        result["status"] = "expired"
    elif result["activated"]:
        result["status"] = "active"
    else:
        result["status"] = "trial"

    return result


# ── 许可证签名（运行时验签防篡改）────────────────────────────────────────────


def _sign_license(expires_at: str) -> str:
    """对 expires_at + machine_hash 做 Ed25519 签名，存入 license_data。

    仅在 activate() 时由作者私钥调用。用户端无私钥，无法生成合法签名。
    返回 base64url 编码的签名字符串。
    """
    private_key = _load_private_key()
    if private_key is None:
        raise ValueError("私钥未找到，无法签发许可证签名。")
    payload = (expires_at + _machine_id()).encode()
    sig = private_key.sign(payload)
    return base64.urlsafe_b64encode(sig).decode()


def _verify_license(data: dict) -> bool:
    """验签：用公钥验证 license_data 中的 signature 是否匹配 expires_at + machine_hash。

    返回 True 表示签名有效，False 表示数据被篡改或缺少签名。
    内部静默处理所有异常（cryptography 未安装、签名格式错误等），统一返回 False。
    """
    sig_b64 = data.get("signature")
    if not sig_b64:
        # 无签名字段 → 旧数据或篡改，视为无效
        return False
    expires_at = data.get("expires_at", "")
    if not expires_at:
        return False
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519

        sig = base64.urlsafe_b64decode(sig_b64)
        payload = (expires_at + _machine_id()).encode()
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(_PUBLIC_KEY_BYTES)
        public_key.verify(sig, payload)
        return True
    except (InvalidSignature, Exception):
        # 签名不匹配 或 任何其他异常 — 篡改证据
        return False


# ── 激活码验证 ────────────────────────────────────────────────────────────────


def _check_activate_rate_limit(company_id: int | None = None) -> bool:
    """检查激活尝试是否超过限流阈值。返回 True 表示允许继续。

    限流状态持久化到 license_data，进程重启不清零。
    """
    now = time.time()
    attempts = _get_activate_attempts(company_id)
    # 清理 60 秒之前的时间戳
    attempts = [t for t in attempts if now - t < 60]
    if len(attempts) >= _MAX_ACTIVATE_ATTEMPTS:
        _save_activate_attempts(attempts, company_id)
        return False
    attempts.append(now)
    _save_activate_attempts(attempts, company_id)
    return True


def activate(code: str, company_id: int | None = None) -> tuple[bool, str]:
    """验证激活码并激活。

    Args:
        code: 激活码字符串
        company_id: 要激活的公司 ID。None 时激活第一个激活的公司。

    Returns:
        (success, message): success=True 表示激活成功。
    """
    if not _check_activate_rate_limit():
        return False, "激活尝试过于频繁，请 60 秒后重试。"

    if not code or len(code.strip()) < 8:
        return False, "无效的激活码格式"

    code = code.strip()
    # 不调 .upper() —— 激活码含 base64url 编码的 Ed25519 签名，大小写敏感

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
    expires_dt = datetime.fromisoformat(expires_at).replace(tzinfo=UTC)

    if now >= expires_dt:
        return False, f"该激活码已到期（有效期至 {expires_at[:10]}）"

    # 写入激活信息（含 Ed25519 签名用于运行时防篡改验签）
    data = _get_license_data(company_id)
    data["activated"] = True
    data["code"] = code
    data["expires_at"] = expires_at
    data["activated_at"] = now.isoformat()
    data["signature"] = _sign_license(expires_at)
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

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric import ed25519

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
    gen.add_argument("request_code", help="用户申请码 (TRADE-REQ-XXXX-XXXX)")
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
