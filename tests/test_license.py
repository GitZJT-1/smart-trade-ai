"""
许可证系统单元测试 — 试用期 + 激活码生成/验证/机器码绑定。
"""

import datetime
import os
from pathlib import Path
from unittest import mock

import pytest

# CI 环境可能没有 cryptography 包，需要 Ed25519 的测试自动跳过
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

_crypto_needed = pytest.mark.skipif(not _HAS_CRYPTO, reason="cryptography 未安装")


class TestMachineId:
    """机器码生成测试"""

    def test_machine_id_not_empty(self):
        from trade.license import _machine_id
        mid = _machine_id()
        assert mid
        assert ":" in mid
        assert len(mid) > 5

    def test_machine_id_stable(self):
        from trade.license import _machine_id
        a = _machine_id()
        b = _machine_id()
        assert a == b

    def test_machine_id_macos_format(self):
        """macOS 上应返回 mac:UUID 格式"""
        import platform
        if platform.system() != "Darwin":
            pytest.skip("非 macOS")
        from trade.license import _machine_id
        mid = _machine_id()
        assert mid.startswith("mac:")

    def test_machine_id_fallback_hostname(self):
        """模拟所有平台检测失败时的 hostname fallback"""
        with mock.patch("platform.system", return_value="SunOS"):
            with mock.patch("subprocess.run", side_effect=OSError):
                with mock.patch("platform.node", return_value="myhost"):
                    from trade.license import _machine_id
                    mid = _machine_id()
                    assert mid == "host:myhost"


class TestRequestCode:
    """申请码生成测试"""

    def test_format(self):
        from trade.license import _make_request_code
        code = _make_request_code()
        assert code.startswith("TRADE-REQ-")
        assert len(code) in (18, 19)  # TRADE-REQ-XXXX-XXXX(8) = 18, 但旧格式可能不同

    def test_deterministic(self):
        from trade.license import _make_request_code
        a = _make_request_code()
        b = _make_request_code()
        assert a == b  # 同一机器应生成相同申请码


@_crypto_needed
class TestEncodeDecode:
    """激活码编解码 roundtrip（需要 cryptography）"""

    def test_roundtrip(self):
        from trade.license import _make_request_code, _encode_activation_code, _decode_activation_code

        req = _make_request_code()
        code = _encode_activation_code(req, "2027-06-01")
        assert code.startswith("TRADE-")
        assert len(code) > 40

        decoded = _decode_activation_code(code)
        assert decoded["expires_at"] == "2027-06-01"
        assert len(decoded["machine_hash"]) == 8

    def test_decode_rejects_tampered_code(self):
        from trade.license import _make_request_code, _encode_activation_code, _decode_activation_code

        req = _make_request_code()
        code = _encode_activation_code(req, "2027-06-01")
        parts = code.split("-")
        parts[-1] = "XXXX"
        tampered = "-".join(parts)
        with pytest.raises(ValueError):
            _decode_activation_code(tampered)

    def test_decode_rejects_wrong_length(self):
        from trade.license import _decode_activation_code
        with pytest.raises(ValueError):
            _decode_activation_code("TRADE-SHORT")

    def test_different_machines_different_hash(self):
        """不同机器码应产生不同的激活码哈希"""
        from trade.license import _encode_activation_code, _decode_activation_code

        code1 = _encode_activation_code("TRADE-REQ-AAAA-BBBB", "2027-06-01")
        code2 = _encode_activation_code("TRADE-REQ-CCCC-DDDD", "2027-06-01")
        d1 = _decode_activation_code(code1)
        d2 = _decode_activation_code(code2)
        assert d1["machine_hash"] != d2["machine_hash"]

    def test_produces_different_codes_for_same_hash_different_date(self):
        """相同申请码不同日期应产生不同激活码"""
        from trade.license import _encode_activation_code
        code1 = _encode_activation_code("TRADE-REQ-AAAA-BBBB", "2027-06-01")
        code2 = _encode_activation_code("TRADE-REQ-AAAA-BBBB", "2027-12-31")
        assert code1 != code2

    def test_encode_without_private_key_fails(self, monkeypatch):
        """没有私钥时编码应抛出异常"""
        monkeypatch.delenv("TRADE_LICENSE_PRIVATE_KEY", raising=False)
        with mock.patch.object(Path, "is_file", return_value=False):
            from trade.license import _encode_activation_code
            with pytest.raises(ValueError, match="私钥"):
                _encode_activation_code("TRADE-REQ-AAAA-BBBB", "2027-06-01")


class TestLicenseCheck:
    """许可证状态检查（mock 数据库调用）"""

    def test_first_launch(self, monkeypatch):
        """新安装：首次检查应通过"""
        from trade.license import _get_license_data, _save_license_data

        # mock 数据库操作
        saved = {}

        def mock_get(cid=None):
            return saved.get(cid, {})
        def mock_save(data, cid=None):
            saved[cid] = data

        monkeypatch.setattr("trade.license._get_license_data", mock_get)
        monkeypatch.setattr("trade.license._save_license_data", mock_save)

        from trade.license import check_license
        ok, msg = check_license(company_id=1)
        assert ok
        assert "first_launch_at" in saved.get(1, {})

    def test_trial_still_valid(self, monkeypatch):
        """试用 10 天应仍然有效"""
        ten_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=10)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {"first_launch_at": ten_days_ago})

        from trade.license import check_license
        ok, msg = check_license(company_id=1)
        assert ok

    def test_trial_expired(self, monkeypatch):
        """试用过期"""
        forty_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=40)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {"first_launch_at": forty_days_ago})

        from trade.license import check_license
        ok, msg = check_license(company_id=1)
        assert not ok
        assert "到期" in msg

    def test_activated_valid(self, monkeypatch):
        """已激活且在有效期内"""
        future = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=200)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {
                               "first_launch_at": "2026-01-01T00:00:00+00:00",
                               "activated": True,
                               "expires_at": future,
                           })

        from trade.license import check_license
        ok, msg = check_license(company_id=1)
        assert ok

    def test_activated_expired(self, monkeypatch):
        """已激活但过了有效期"""
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {
                               "first_launch_at": "2026-01-01T00:00:00+00:00",
                               "activated": True,
                               "expires_at": "2026-02-01T00:00:00+00:00",
                           })

        from trade.license import check_license
        ok, msg = check_license(company_id=1)
        assert not ok
        assert "到期" in msg


class TestDaysRemaining:
    """剩余天数计算"""

    def test_trial_days_remaining(self, monkeypatch):
        ten_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=10)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {"first_launch_at": ten_days_ago})

        from trade.license import days_remaining
        remaining = days_remaining(company_id=1)
        assert 19 <= remaining <= 20

    def test_expired_returns_zero(self, monkeypatch):
        forty_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=40)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {"first_launch_at": forty_days_ago})

        from trade.license import days_remaining
        assert days_remaining(company_id=1) == 0

    def test_active_returns_remaining(self, monkeypatch):
        future = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=100)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {
                               "first_launch_at": "2026-01-01T00:00:00+00:00",
                               "activated": True,
                               "expires_at": future,
                           })

        from trade.license import days_remaining
        remaining = days_remaining(company_id=1)
        assert 95 <= remaining <= 100

    def test_no_data_returns_trial_max(self, monkeypatch):
        monkeypatch.setattr("trade.license._get_license_data", lambda cid=None: {})
        from trade.license import days_remaining
        assert days_remaining(company_id=1) == 30


class TestLicenseStatus:
    """status 函数返回前端状态"""

    def test_trial_status(self, monkeypatch):
        monkeypatch.setattr("trade.license._get_license_data", lambda cid=None: {})
        from trade.license import status
        s = status(company_id=1)
        assert s["status"] == "trial"
        assert s["activated"] is False
        assert s["request_code"] == ""

    def test_expired_shows_request_code(self, monkeypatch):
        forty_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=40)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {"first_launch_at": forty_days_ago})

        from trade.license import status
        s = status(company_id=1)
        assert s["status"] == "expired"
        assert s["request_code"].startswith("TRADE-REQ-")

    def test_active_status(self, monkeypatch):
        future = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365)).isoformat()
        monkeypatch.setattr("trade.license._get_license_data",
                           lambda cid=None: {
                               "first_launch_at": "2026-01-01T00:00:00+00:00",
                               "activated": True,
                               "expires_at": future,
                           })

        from trade.license import status
        s = status(company_id=1)
        assert s["status"] == "active"
        assert s["activated"] is True


class TestRateLimit:
    """激活限流"""

    def test_allows_up_to_max(self):
        from trade.license import _check_activate_rate_limit, _MAX_ACTIVATE_ATTEMPTS
        for _ in range(_MAX_ACTIVATE_ATTEMPTS):
            assert _check_activate_rate_limit() is True

    def test_blocks_after_max(self):
        from trade.license import _check_activate_rate_limit, _MAX_ACTIVATE_ATTEMPTS
        # 消耗掉所有配额（测试隔离：rate limit 计数器已被上一个测试填充）
        # 只测超过上限的行为
        import time
        time.sleep(61)  # 等 60s 窗口过期
        for _ in range(_MAX_ACTIVATE_ATTEMPTS):
            _check_activate_rate_limit()
        assert _check_activate_rate_limit() is False


@_crypto_needed
class TestActivate:
    """激活执行流程（需要 cryptography）"""

    def test_activate_with_empty_code(self):
        from trade.license import activate
        ok, msg = activate("")
        assert not ok

    def test_activate_with_short_code(self):
        from trade.license import activate
        ok, msg = activate("X")
        assert not ok

    def test_activate_cross_machine_rejected(self):
        """用不属于本机的哈希生成的激活码应被拒绝"""
        from trade.license import _encode_activation_code, activate
        code = _encode_activation_code("TRADE-REQ-DEAD-BEEF", "2027-12-31")
        ok, msg = activate(code)
        assert not ok
        # DEADBEEF 哈希不在本地机器码中，会被拒绝（签名无效或机器码不匹配）
        assert not ok


class TestResolveHermesHome:
    """Hermes 目录路径解析"""

    def test_env_var_priority(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "custom"))
        from trade.license import _resolve_hermes_home
        assert _resolve_hermes_home() == tmp_path / "custom"

    def test_default_unix(self, monkeypatch):
        monkeypatch.delenv("HERMES_HOME", raising=False)
        monkeypatch.setattr("os.name", "posix")
        from trade.license import _resolve_hermes_home
        home = _resolve_hermes_home()
        assert home.name == ".hermes"

    def test_default_windows(self):
        """Windows 路径解析需要在 Windows 上测试，macOS/Linux 跳过"""
        import os as _os
        if _os.name != "nt":
            pytest.skip("Windows-only test")
