# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TradeWin single-exe build."""
import sys
from pathlib import Path

_block_cipher = None
_PROJECT_ROOT = Path(SPECPATH).parent.parent
_TRADEWIN_ROOT = Path(SPECPATH)

a = Analysis(
    [str(_TRADEWIN_ROOT / 'tradewin' / 'main.py')],
    pathex=[str(_TRADEWIN_ROOT), str(_PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(_TRADEWIN_ROOT / 'tradewin' / 'resources' / 'icon.ico'), 'tradewin/resources'),
        (str(_TRADEWIN_ROOT / 'tradewin' / 'resources' / 'style.qss'), 'tradewin/resources'),
        (str(_PROJECT_ROOT / 'skills'), 'skills'),
        (str(_PROJECT_ROOT / '.trade-template'), '.trade-template'),
        (str(_PROJECT_ROOT / 'trade'), 'trade'),
    ],
    hiddenimports=[
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'uvicorn.loops.auto', 'uvicorn.protocols.http.auto',
        'trade', 'trade.api', 'trade.api.chat', 'trade.api.cron',
        'trade.api.companies', 'trade.api.customers', 'trade.api.libraries',
        'trade.api.orders', 'trade.api.conversations', 'trade.api.memory',
        'trade.api.onboarding', 'trade.api.license', 'trade.api.deps',
        'trade.database', 'trade.company', 'trade.company.crud', 'trade.company.workdir',
        'trade.helpers', 'trade.prompts', 'trade.prompt',
        'trade.skill_router', 'trade.skill_registry',
        'trade.chat_memory', 'trade.memory', 'trade.license',
        'trade.onboarding', 'trade.bootstrap',
        'trade.osint', 'trade.osint.orchestrator', 'trade.osint.whois',
        'trade.osint.email_verify', 'trade.osint.sanctions', 'trade.osint.sanctions.loader',
        'trade.osint.tech_stack', 'trade.osint.linkedin_verify',
        'trade.osint.scoring', 'trade.osint.constants',
        'hermes_cli', 'hermes_cli.config', 'hermes_cli.auth',
        'hermes_cli.env_loader', 'hermes_cli.models',
        'hermes_constants', 'run_agent',
        'asyncio', 'sqlite3', 'json', 'csv', 'io', 're', 'hashlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=_block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=_block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    [],
    name='TradeWin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_TRADEWIN_ROOT / 'tradewin' / 'resources' / 'icon.ico'),
)
