"""
py2app setup script — builds a standalone macOS .app bundle.

Usage:
    python3 setup_mac.py py2app

The result is placed in dist/EOD Reporter.app
"""

from setuptools import setup

APP = ["desktop/main.py"]
from pathlib import Path

_ICON = Path("desktop/assets/icon.icns")
DATA_FILES = []
_ICONFILE = str(_ICON) if _ICON.exists() else None

OPTIONS = {
    "argv_emulation": False,
    **({"iconfile": _ICONFILE} if _ICONFILE else {}),
    "plist": {
        "CFBundleName": "EOD Reporter",
        "CFBundleDisplayName": "EOD Auto Reporter",
        "CFBundleIdentifier": "com.eod-reporter.desktop",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
    },
    "packages": [
        "app",
        "app.models",
        "app.services",
        "desktop",
        "desktop.views",
        "customtkinter",
        "pydantic",
        "pydantic_settings",
        "slack_sdk",
        "requests",
        "apscheduler",
    ],
    "includes": [
        "tkinter",
        "PIL",
    ],
}

setup(
    app=APP,
    name="EOD Reporter",
    data_files=DATA_FILES,
    package_data={"desktop": ["assets/*.png"]} if (Path("desktop/assets/icon.png").exists()) else {},
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
