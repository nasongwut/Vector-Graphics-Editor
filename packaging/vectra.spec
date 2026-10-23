# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Vectra — run from the repo root:
#     pyinstaller --noconfirm --clean packaging/vectra.spec
# Produces dist/Vectra/ (Windows, one-folder, used by the Inno Setup installer)
# or dist/Vectra.app (macOS).

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
PKG = os.path.join(ROOT, "packaging")

with open(os.path.join(ROOT, "vectra", "__init__.py"), encoding="utf-8") as f:
    VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', f.read()).group(1)

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")
# macOS: build for the runner's own CPU (x86_64 on Intel, arm64 on Apple Silicon)
TARGET_ARCH = os.environ.get("VECTRA_TARGET_ARCH") or None

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "vectra", "assets"), "vectra/assets")],
    hiddenimports=[],
    excludes=["unittest", "pydoc", "test", "lib2to3", "pip", "setuptools"],
    noarchive=False,
)
pyz = PYZ(a.pure)

version_file = os.path.join(PKG, "windows", "version_info.txt") if IS_WIN else None
if version_file and not os.path.exists(version_file):
    version_file = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Vectra",
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=TARGET_ARCH,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PKG, "vectra.icns" if IS_MAC else "vectra.ico"),
    version=version_file,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Vectra")

if IS_MAC:
    DOC_TYPES = [
        ("Adobe Illustrator Document", ["ai"], "com.adobe.illustrator.ai-image"),
        ("Encapsulated PostScript", ["eps", "epsf", "ps"], "com.adobe.encapsulated-postscript"),
        ("PDF Document", ["pdf"], "com.adobe.pdf"),
        ("Vectra Document", ["json"], "public.json"),
    ]
    app = BUNDLE(
        coll,
        name="Vectra.app",
        icon=os.path.join(PKG, "vectra.icns"),
        bundle_identifier="th.co.cityart.vectra",
        version=VERSION,
        info_plist={
            "CFBundleName": "Vectra",
            "CFBundleDisplayName": "Vectra",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSApplicationCategoryType": "public.app-category.graphics-design",
            "CFBundleDocumentTypes": [
                {"CFBundleTypeName": name, "CFBundleTypeExtensions": exts,
                 "LSItemContentTypes": [uti], "CFBundleTypeRole": "Editor",
                 "LSHandlerRank": "Alternate"}
                for name, exts, uti in DOC_TYPES
            ],
        },
    )
