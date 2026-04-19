# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec：单文件、无控制台窗口。在项目根目录执行:
#   pyinstaller case_analysis.spec
#
# 注：SPECPATH 由 PyInstaller 注入，为包含本 spec 的目录。

from pathlib import Path

_spec_dir = Path(SPECPATH)  # type: ignore[name-defined]

block_cipher = None

hiddenimports = [
    "pymysql",
    "sqlalchemy.dialects.mysql.pymysql",
    "openpyxl",
    "xlrd",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(_spec_dir)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
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
    name="case_analysis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
