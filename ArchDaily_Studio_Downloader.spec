# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [('ui', 'ui'), ('icon.ico', '.'), ('icon.png', '.')]
binaries = []
hiddenimports = []

tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

excludes = [
    'tkinter', '_tkinter', 'customtkinter',
    'numpy', 'scipy', 'matplotlib', 'pandas', 'PIL', 'Pillow',
    'unittest', 'test', 'pydoc', 'xmlrpc',
    'curses', 'turtle', 'sqlite3'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure, optimize=2)

upx_dir = r"C:\Users\MSI\AppData\Local\Microsoft\WinGet\Packages\UPX.UPX_Microsoft.Winget.Source_8wekyb3d8bbwe\upx-5.2.1-win64"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ArchDaily_Studio_Downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_dir=upx_dir,
    upx_exclude=['vcruntime140.dll', 'python314.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='file_version_info.txt',
    icon=['icon.ico'],
    manifest='app.manifest',
)
