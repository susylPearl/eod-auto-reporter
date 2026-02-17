"""
py2app setup script — builds a standalone macOS .app bundle.

Usage:
    python3 setup_mac.py py2app

The result is placed in dist/EOD Reporter.app
"""

from setuptools import setup

APP = ["desktop/main.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,  # Replace with "desktop/assets/icon.icns" when available
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
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
