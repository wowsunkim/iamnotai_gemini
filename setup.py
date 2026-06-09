"""py2app build script — Intel Mac .app 번들 생성
실행: python setup.py py2app
"""
import os
from setuptools import setup

CONDA_LIB = os.path.expanduser("~/pinokio/bin/miniconda/lib")

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "CFBundleName": "im-not-ai",
        "CFBundleDisplayName": "im-not-ai",
        "CFBundleIdentifier": "com.iamnotai.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.13.0",
        "NSHumanReadableCopyright": "MIT License",
    },
    "packages": [],
    "includes": ["tkinter", "json", "threading", "urllib"],
    "excludes": ["numpy", "scipy", "matplotlib", "PIL", "wx", "PyQt5", "PyQt6"],
    "arch": "x86_64",
    # conda 환경의 dylib — py2app이 자동 탐지하지 못하는 것들을 명시
    "frameworks": [
        os.path.join(CONDA_LIB, "libffi.8.dylib"),
        os.path.join(CONDA_LIB, "libtcl8.6.dylib"),
        os.path.join(CONDA_LIB, "libtk8.6.dylib"),
    ],
}

setup(
    name="im-not-ai",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
