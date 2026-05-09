# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包规格文件
用法: pyinstaller app.spec
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

_a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/resources/*.svg', 'app/resources'),  # 图标资源
        ('app/resources/qt.conf', 'PyQt6/Qt6'),    # Qt 插件配置（定位 platforms/styles 等）
    ] + collect_data_files('airportsdata'),          # airportsdata CSV 数据文件
    hiddenimports=[
        'openpyxl',
        'xlwt',
        'xlrd',
        'cpca',
        'airportsdata',
        'lxml',
        'sqlalchemy',
        'pandas',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tests',
        'pytest',
        'unittest',
        'setuptools',
        'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

_pyz = PYZ(
    _a.pure, _a.zipped_data,
    cipher=None,
)

_exe = EXE(
    _pyz,
    _a.scripts,
    _a.binaries,
    _a.zipfiles,
    _a.datas,
    [],
    name='案件侦查数据分析系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

_coll = COLLECT(
    _exe,
    _a.binaries,
    _a.zipfiles,
    _a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='案件侦查数据分析系统',
)
