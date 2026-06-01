# License 机器码绑定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 激活码绑定本机硬件，一个码只能在一台机器上使用。到期界面自动显示申请码。

**Architecture:** 后端 `trade/license.py` 新增 `_machine_id()` 取本机硬件指纹（macOS 取 IOPlatformUUID，Linux 取 machine-id，Windows 取注册表 MachineGuid）。`generate` 命令改为接收申请码+日期，生成的激活码内嵌机器码哈希。`activate()` 验证时比对机器码。前端 `/api/trade/license/status` 返回中新增 `request_code` 字段，到期界面自动显示。

**Tech Stack:** Python stdlib (platform, subprocess, hashlib, hmac)

---

### Task 1: 后端 — 添加机器码生成函数

**Files:**
- Modify: `trade/license.py`

- [ ] **Step 1: 在 `trade/license.py` 顶部新增 `_machine_id()` 函数**

在 `_SECRET` 定义之后、`_TRIAL_DAYS` 之前插入：

```python
def _machine_id() -> str:
    """获取本机唯一硬件标识符。

    macOS → IOPlatformUUID (稳定，重装系统前不变)
    Linux   → /etc/machine-id
    Windows → 注册表 MachineGuid
    其他平台 → hostname (fallback)
    """
    import platform as _platform
    import subprocess as _sp

    sys_name = _platform.system()
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
        try:
            mid = Path("/etc/machine-id").read_text().strip()
            if mid:
                return f"linux:{mid}"
        except Exception:
            pass
        try:
            mid = Path("/var/lib/dbus/machine-id").read_text().strip()
            if mid:
                return f"linux:{mid}"
        except Exception:
            pass

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

    return f"host:{_platform.node()}"
```

- [ ] **Step 2: 运行测试确保导入正常**

```bash
python -m pytest tests/ -x -q
```

- [ ] **Step 3: Commit**

```bash
git add trade/license.py
git commit -m "feat: license 添加本机硬件标识符 _machine_id()"
```

---

### Task 2: 后端 — status 接口返回申请码

**Files:**
- Modify: `trade/license.py` (status 函数)

- [ ] **Step 1: 修改 `status()` 函数，增加 `request_code` 字段**

找到 `status()` 函数中 `result: dict = {...}` 块，在 `"status": ...` 计算之前，向 result 增加 `request_code`：

```python
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
        "request_code": "",  # 未到期时不显示
    }

    if "first_launch_at" in data:
        first = datetime.fromisoformat(data["first_launch_at"])
        result["trial_used"] = min((now - first).days, _TRIAL_DAYS)

    if not result["activated"] and result["days_remaining"] <= 0:
        result["status"] = "expired"
        # 到期时生成申请码
        result["request_code"] = _make_request_code()
    elif result["activated"]:
        result["status"] = "active"
    else:
        result["status"] = "trial"

    return result
```

- [ ] **Step 2: 新增 `_make_request_code()` 函数**

在 `_machine_id()` 之后、`_get_license_data()` 之前添加：

```python
def _make_request_code() -> str:
    """生成本机申请码: TRADE-REQ-XXXX-XXXX（基于机器码哈希）。"""
    mid = _machine_id()
    h = hashlib.sha256(mid.encode()).hexdigest()[:12].upper()
    return f"TRADE-REQ-{h[:4]}-{h[4:8]}-{h[8:12]}"
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add trade/license.py
git commit -m "feat: license status 返回 request_code，到期时自动生成申请码"
```

---

### Task 3: 后端 — 激活码编解码支持机器码

**Files:**
- Modify: `trade/license.py` (_encode_activation_code, _decode_activation_code)

- [ ] **Step 1: 重写 `_encode_activation_code` 接收申请码+日期**

```python
def _encode_activation_code(request_code: str, expires_at: str) -> str:
    """根据申请码和到期日期生成激活码。

    激活码内嵌申请码哈希 + 到期日期 + HMAC 签名。

    Args:
        request_code: 用户发送的申请码 (TRADE-REQ-XXXX-XXXX-XXXX)
        expires_at: ISO 日期字符串，如 "2027-06-01"

    Raises:
        ValueError: TRADE_LICENSE_SECRET 未设置
    """
    if not _SECRET:
        raise ValueError("TRADE_LICENSE_SECRET 环境变量未设置，无法生成激活码。")

    # 从申请码提取机器码哈希（去掉 TRADE-REQ- 前缀和连字符）
    req_core = request_code.replace("TRADE-REQ-", "").replace("-", "").upper()
    date_part = expires_at[:10].replace("-", "")  # YYYYMMDD

    # 签名: HMAC(date + req_core)
    sig_payload = (date_part + req_core).encode()
    sig = hmac.new(_SECRET, sig_payload, hashlib.sha256).hexdigest()[:8]

    combined = (date_part + req_core + sig).encode()
    b64 = _base64url_encode(combined)
    return f"TRADE-{b64[:4]}-{b64[4:8]}-{b64[8:12]}-{b64[12:16]}".upper()
```

- [ ] **Step 2: 重写 `_decode_activation_code` 返回申请码哈希和到期日期**

```python
def _decode_activation_code(code: str) -> dict:
    """解码激活码，返回 {expires_at: str, machine_hash: str}。"""
    core = code.replace("TRADE-", "").replace("-", "").upper()
    decoded = _base64url_decode(core)

    date_part = decoded[:8].decode()
    expires_at = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
    req_hash = decoded[8:20].decode()   # 12 位机器码哈希
    sig_part = decoded[20:].decode()     # 8 位 HMAC 签名

    # 验证签名
    sig_payload = (date_part + req_hash).encode()
    expected_sig = hmac.new(_SECRET, sig_payload, hashlib.sha256).hexdigest()[:8]
    if not hmac.compare_digest(sig_part, expected_sig):
        raise ValueError("Invalid activation code signature")

    return {"expires_at": expires_at, "machine_hash": req_hash}
```

- [ ] **Step 3: 修改 `activate()` 函数增加机器码验证**

在 `activate()` 中，`_decode_activation_code` 之后、过期检查之前，加机器码比对：

```python
    # 解码激活码
    try:
        decoded = _decode_activation_code(code)
    except Exception:
        return False, "激活码无效"

    # 验证机器码：本机哈希必须匹配激活码中的哈希
    local_machine_hash = hashlib.sha256(_machine_id().encode()).hexdigest()[:12].upper()
    if not hmac.compare_digest(local_machine_hash, decoded["machine_hash"]):
        return False, "此激活码不适用于本机。请在本机上生成申请码后联系作者。"
```

- [ ] **Step 4: 修改 CLI `generate` 子命令接收申请码参数**

```python
if args.cmd == "generate":
    code = _encode_activation_code(args.request_code, args.date)
    print(f"激活码: {code}")
```

修改 argparse 部分：

```python
gen = sub.add_parser("generate", help="生成激活码")
gen.add_argument("request_code", help="用户申请码 (TRADE-REQ-XXXX-XXXX-XXXX)")
gen.add_argument("date", help="到期日期 (YYYY-MM-DD)")
```

- [ ] **Step 5: 运行测试**

```bash
python -m pytest tests/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add trade/license.py
git commit -m "feat: license 激活码编码内嵌机器码哈希，激活时验证本机硬件"
```

---

### Task 4: 前端 — 到期界面显示申请码

**Files:**
- Modify: `static/trade_chat.html`

- [ ] **Step 1: 修改 `loadLicenseStatus()` 显示申请码**

找到 `loadLicenseStatus` 函数（约第 605 行），`status === 'expired'` 分支中，在现有提示后面加上申请码显示。找到这段代码：

```javascript
    if (data.status === 'expired' || (data.status === 'trial' && data.days_remaining <= 0)) {
        bar.style.background = '#FEF2F2';
        bar.style.color = '#DC2626';
        bar.innerHTML = '试用期已到期 · <a href="#" onclick="showActivateModal()" style="color:#DC2626;text-decoration:underline;">输入激活码</a>';
        bar.style.display = 'block';
        return;
    }
```

扩展申请码显示逻辑，读取 `data.request_code`：

```javascript
    if (data.status === 'expired' || (data.status === 'trial' && data.days_remaining <= 0)) {
        bar.style.background = '#FEF2F2';
        bar.style.color = '#DC2626';
        var reqHtml = '试用期已到期 · <a href="#" onclick="showActivateModal()" style="color:#DC2626;text-decoration:underline;">输入激活码</a>';
        if (data.request_code) {
            reqHtml += ' · 申请码: <code style="background:#FEE2E2;padding:1px 6px;border-radius:3px;font-size:11px;user-select:all;cursor:text;">' + data.request_code + '</code>';
        }
        bar.innerHTML = reqHtml;
        bar.style.display = 'block';
        return;
    }
```

- [ ] **Step 2: 同步到运行目录 + 提交**

```bash
cp static/trade_chat.html ~/.trade/foreign-trade-assistant/static/trade_chat.html
git add static/trade_chat.html
git commit -m "feat: 到期界面显示申请码"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 测试 `_machine_id()` 可正常返回非空字符串**

```bash
python -c "from trade.license import _machine_id; print(_machine_id())"
```
期望：输出类似 `mac:XXXX-XXXX-XXXX` 的字符串

- [ ] **Step 2: 测试生成申请码**

```bash
python -c "from trade.license import _make_request_code; print(_make_request_code())"
```
期望：输出 `TRADE-REQ-XXXX-XXXX-XXXX`

- [ ] **Step 3: 测试完整编解码流程**

```bash
# 先设 secret
export TRADE_LICENSE_SECRET=test-secret-key-for-dev
# 生成申请码
REQ=$(python -c "from trade.license import _make_request_code; print(_make_request_code())")
# 用申请码生成激活码
CODE=$(python -c "from trade.license import _encode_activation_code; print(_encode_activation_code('$REQ', '2027-06-01'))")
echo "Request: $REQ"
echo "Code: $CODE"
# 解码验证
python -c "
from trade.license import _decode_activation_code
d = _decode_activation_code('$CODE')
print('expires:', d['expires_at'])
print('hash:', d['machine_hash'])
"
```
期望：解码成功，输出到期日和机器码哈希

- [ ] **Step 5: 运行全部测试**

```bash
python -m pytest tests/ -x -q
```

- [ ] **Step 6: Commit 和 push**

```bash
git push
```

---

### 使用说明（给作者）

生成 secret（仅首次）：
```bash
python -m trade.license generate-secret
# 将输出的 TRADE_LICENSE_SECRET=xxx 写入 ~/.hermes/.env
```

用户发来申请码后，生成激活码：
```bash
python -m trade.license generate TRADE-REQ-XXXX-XXXX-XXXX 2027-06-01
```

输出激活码发给用户即可。
