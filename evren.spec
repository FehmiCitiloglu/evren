# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec dosyası - evren masaüstü uygulaması.

macOS (evren.app), Windows (evren.exe) ve Linux (evren)
için tek tıkla çalıştırılabilir ikili (binary) paketler üretir.
"""
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    "keyring.backends.macOS",
    "keyring.backends.Windows",
    "keyring.backends.SecretService",
    "keyring.backends.chainer",
    "PIL._tkinter_finder",
]

# CustomTkinter varlıkları (fontlar, JSON tema dosyaları, ikonlar)
ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")
datas += ctk_datas
binaries += ctk_binaries
hiddenimports += ctk_hidden

# Certifi SSL kök sertifikaları (HTTPS istekleri için)
cert_datas, cert_binaries, cert_hidden = collect_all("certifi")
datas += cert_datas
binaries += cert_binaries
hiddenimports += cert_hidden

# evren_agent paket verileri (openapi.json, builtin_skills, assets)
evren_datas, evren_binaries, evren_hidden = collect_all("evren_agent")
datas += evren_datas
binaries += evren_binaries
hiddenimports += evren_hidden

# Varsa assets dosyalarını garantiye al
assets_dir = Path("evren_agent/ui/assets")
if assets_dir.exists():
    datas.append((str(assets_dir), "evren_agent/ui/assets"))

is_mac = sys.platform == "darwin"
is_win = sys.platform == "win32"

icon_file = None
if is_mac and Path("evren_agent/ui/assets/icon.png").exists():
    icon_file = "evren_agent/ui/assets/icon.png"
elif is_win and Path("evren_agent/ui/assets/icon.ico").exists():
    icon_file = "evren_agent/ui/assets/icon.ico"
elif Path("evren_agent/ui/assets/icon.png").exists():
    icon_file = "evren_agent/ui/assets/icon.png"

a = Analysis(
    ["evren_agent/ui/__main__.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="evren",
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
    icon=icon_file,
)

if is_mac:
    app = BUNDLE(
        exe,
        name="evren.app",
        icon=icon_file,
        bundle_identifier="ssyz.evren.desktop",
        info_plist={
            "CFBundleName": "evren",
            "CFBundleDisplayName": "evren",
            "CFBundleGetInfoString": "EVREN LLM API Masaüstü Uygulaması",
            "CFBundleIdentifier": "ssyz.evren.desktop",
            "CFBundleVersion": "0.2.0",
            "CFBundleShortVersionString": "0.2.0",
            "NSHighResolutionCapable": "True",
        },
    )
