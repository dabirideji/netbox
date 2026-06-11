# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Netbox monitor backend."""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
BACKEND_ROOT = ROOT / "backend"
SRC_ROOT = BACKEND_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

block_cipher = None

a = Analysis(
    [str(BACKEND_ROOT / "monitor.py")],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "netbox",
        "netbox.__main__",
        "netbox.checks",
        "netbox.cli",
        "netbox.config",
        "netbox.models",
        "netbox.network",
        "netbox.paths",
        "netbox.ping",
        "netbox.scheduler",
        "netbox.server",
        "netbox.state",
        "netbox.storage",
        "netbox.summary",
        "netbox.targets",
        "netbox.terminal",
        "netbox.timeutils",
        "netbox.validation",
        "netbox.wallpaper",
        "netbox.speed",
        "netbox.crypto",
        "netbox.alerts",
        "netbox.alerts.dispatcher",
        "netbox.alerts.models",
        "netbox.alerts.smtp_client",
        "netbox.storage.alerts",
        "cryptography",
        "cryptography.fernet",
        "dns",
        "dns.resolver",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="netbox-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
