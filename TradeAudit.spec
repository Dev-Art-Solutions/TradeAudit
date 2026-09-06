# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

block_cipher = None

project_dir = Path.cwd()
src_dir = project_dir / "src"
resources_dir = project_dir / "resources"

datas = []
if resources_dir.exists():
    datas.append((str(resources_dir), "resources"))

webui_static_dir = src_dir / "tradeaudit" / "webui" / "static"
if webui_static_dir.exists():
    datas.append((str(webui_static_dir), "tradeaudit/webui/static"))

hidden_imports = [
    "keyring.backends",
    "keyring.backends.Windows",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.sql.default_comparator",
    "pydantic_settings",
    "pydantic",
    "fastapi",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "webview",
]

# Optional MT5 import
try:
    import MetaTrader5
    hidden_imports.append("MetaTrader5")
except ImportError:
    pass

a = Analysis(
    [str(src_dir / "tradeaudit" / "__main__.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TradeAudit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(resources_dir / "icons" / "tradeaudit.ico") if (resources_dir / "icons" / "tradeaudit.ico").exists() else None,
    version=str(resources_dir / "version_info.txt") if (resources_dir / "version_info.txt").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TradeAudit",
)
