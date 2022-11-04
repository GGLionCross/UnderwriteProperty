# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['underwrite-property.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.')],
    hiddenimports=[],
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
    name='underwrite-property',
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

import shutil
import os
import subprocess

# Copies config.json and README.me to DISTPATH
shutil.copyfile('config.json', '{0}/config.json'.format(DISTPATH))
shutil.copyfile('README.md', '{0}/README.md'.format(DISTPATH))

path_7zip = r"C:\Program Files\7-Zip\7z.exe"
outfile_name = "underwrite-property.zip"

def sevenzip(filename, zipname):
    system = subprocess.Popen([path_7zip, "a", zipname, filename])
    return(system.communicate())

# Zips all files in distribution to under-property.zip
sevenzip(f"{SPECPATH}\\dist\\*", outfile_name)

# Copies all files in distribution to untracked folder for personal usage
IGNORE = f"{SPECPATH}\\.ignore"
shutil.copytree(DISTPATH, IGNORE, dirs_exist_ok=True)

# Overwrite .ignore\config.json with .ignore\keep-config.json
# This is so I don't have to keep updating my creds in config.json
shutil.copyfile('{0}/keep-config.json'.format(IGNORE), '{0}/config.json'.format(IGNORE))