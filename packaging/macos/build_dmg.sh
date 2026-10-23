#!/usr/bin/env bash
# Build dist/Vectra.app with PyInstaller and wrap it in a drag-to-Applications DMG.
# Usage (from the repo root, on a Mac):   bash packaging/macos/build_dmg.sh
# Output: dist/Vectra-<version>-macos-<arm64|x86_64>.dmg
set -euo pipefail
cd "$(dirname "$0")/../.."

ARCH="${VECTRA_TARGET_ARCH:-$(uname -m)}"
export VECTRA_TARGET_ARCH="$ARCH"
VERSION=$(python3 -c "import re;print(re.search(r'__version__\s*=\s*\"([^\"]+)\"',open('vectra/__init__.py').read()).group(1))")

python3 -m PyInstaller --noconfirm --clean packaging/vectra.spec

APP="dist/Vectra.app"
# ad-hoc signature so Apple Silicon will launch it (no Developer ID needed)
codesign --force --deep --sign - "$APP"

STAGE="dist/dmg"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
case "$ARCH" in arm64) LABEL="apple-silicon" ;; *) LABEL="intel" ;; esac
DMG="dist/Vectra-${VERSION}-macos-${LABEL}.dmg"
rm -f "$DMG"
hdiutil create -volname "Vectra ${VERSION}" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
echo "built $DMG"
