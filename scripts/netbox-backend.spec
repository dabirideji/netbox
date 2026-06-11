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
    datas=[
        (str(SRC_ROOT / "openapi.yaml"), "."),
        (str(SRC_ROOT / "docs"), "docs"),
        (str(SRC_ROOT / "schemas"), "schemas"),
    ],
    hiddenimports=[
        "netbox",
        "netbox.__main__",
        "netbox.cli",
        "netbox.cli.app",
        "netbox.config",
        "netbox.config.loader",
        "netbox.core",
        "netbox.core.models",
        "netbox.core.responses",
        "netbox.util",
        "netbox.util.crypto",
        "netbox.util.paths",
        "netbox.util.timeutils",
        "netbox.util.validation",
        "netbox.probes",
        "netbox.probes.checks",
        "netbox.probes.network",
        "netbox.probes.ping",
        "netbox.monitor",
        "netbox.monitor.scheduler",
        "netbox.monitor.speed",
        "netbox.monitor.state",
        "netbox.monitor.summary",
        "netbox.monitor.terminal",
        "netbox.server",
        "netbox.server.api_docs",
        "netbox.server.wallpaper",
        "netbox.storage",
        "netbox.targets",
        "netbox.targets.registry",
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
