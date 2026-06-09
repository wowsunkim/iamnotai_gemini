"""py2app build script — Mac .app 번들 생성
실행: python3 setup.py py2app
"""
from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "CFBundleName": "im-not-ai",
        "CFBundleDisplayName": "im-not-ai",
        "CFBundleIdentifier": "com.iamnotai.app",
        "CFBundleVersion": "1.1.0",
        "CFBundleShortVersionString": "1.1",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.13.0",
        "NSHumanReadableCopyright": "MIT License",
    },
    "packages": [],
    "includes": ["tkinter", "json", "threading", "urllib"],
    "excludes": ["numpy", "scipy", "matplotlib", "PIL", "wx", "PyQt5", "PyQt6"],
}

setup(
    name="im-not-ai",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
