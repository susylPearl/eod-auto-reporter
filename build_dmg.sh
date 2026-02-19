#!/bin/bash
#
# Build EOD Reporter as a macOS .app and create a DMG for distribution.
#
# Prerequisites:
#   pip install -r requirements.txt -r requirements-desktop.txt
#   (py2app is in requirements-desktop.txt)
#
# Usage:
#   ./build_dmg.sh
#
# Output:
#   dist/EOD Reporter.app
#   dist/EOD-Reporter-1.0.0.dmg

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="EOD Reporter"
DMG_NAME="EOD-Reporter-1.0.0"
VOLUME_NAME="EOD Reporter"

echo "=== Building $APP_NAME.app with py2app ==="
python3 setup_mac.py py2app

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "Error: $APP_PATH not found after build"
    exit 1
fi

echo "=== Creating DMG ==="
DMG_TMP="dist/dmg-tmp"
DMG_OUT="dist/${DMG_NAME}.dmg"

rm -rf "$DMG_TMP"
mkdir -p "$DMG_TMP"

# Copy app to temp folder
cp -R "$APP_PATH" "$DMG_TMP/"

# Create DMG using hdiutil
rm -f "$DMG_OUT"
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "$DMG_TMP" \
    -ov -format UDZO \
    "$DMG_OUT"

# Cleanup
rm -rf "$DMG_TMP"

echo ""
echo "=== Build complete ==="
echo "  App:  $APP_PATH"
echo "  DMG:  $DMG_OUT"
echo ""
echo "To install: open the DMG and drag $APP_NAME to Applications."
