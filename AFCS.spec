# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None

project_dir = Path.cwd()

# 폴더 내 모든 파일을 (src, dest) 2-튜플로 수집
def collect_dir(src_dir: Path, dest_prefix: str):
    if not src_dir.exists():
        return []
    return [(str(p), dest_prefix) for p in src_dir.rglob('*') if p.is_file()]

datas = []
datas += collect_dir(project_dir / 'icons', 'icons')
datas += collect_dir(project_dir / 'rangeTables', 'rangeTables')

a = Analysis(
    ['app.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=['tkinter', 'tkinter.ttk', '_tkinter'],
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
    name='AFCS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,  # one-file
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)