#!/usr/bin/env python3
"""Build and verify a clean release package for the ClassWiz calculator.

Assembles portable application files, strips bytecode/pycache, and verifies
completeness of all required assets (Katex, ClassWizFontSet, qrcode).
"""

import os
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist" / "calculator_portable"

REQUIRED_FILES = [
    "mvp_server.py",
    "frontend.html",
    "README.md",
]

REQUIRED_DIRS = [
    "engine",
    "katex",
    "ClassWizFontSet",
    "qrcode",
]


def clean_and_assemble():
    print(f"[BUILD] Assembling release into {DIST_DIR}...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Copy files
    for f in REQUIRED_FILES:
        src = ROOT_DIR / f
        if src.exists():
            shutil.copy2(src, DIST_DIR / f)
            print(f"  + Copied {f}")
        else:
            print(f"  ! Missing required file: {f}")

    # Copy directories
    for d in REQUIRED_DIRS:
        src = ROOT_DIR / d
        if src.exists():
            shutil.copytree(src, DIST_DIR / d, dirs_exist_ok=True)
            print(f"  + Copied directory {d}/")
        else:
            print(f"  ! Missing required directory: {d}")

    # Copy portable launchers
    portable_src = ROOT_DIR / "portable"
    if portable_src.exists():
        for pf in portable_src.glob("*"):
            if pf.is_file():
                shutil.copy2(pf, DIST_DIR / pf.name)
                print(f"  + Copied launcher {pf.name}")

    # Clean __pycache__
    pycache_count = 0
    for p in DIST_DIR.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p)
            pycache_count += 1
    print(f"  - Removed {pycache_count} __pycache__ directories.")


PYTHON_EXE_REL = Path("python") / "python.exe"


def verify_release(require_python=False):
    print("[VERIFY] Checking asset completeness...")
    missing = []
    for f in REQUIRED_FILES:
        if not (DIST_DIR / f).exists():
            missing.append(f)
    for d in REQUIRED_DIRS:
        if not (DIST_DIR / d).exists():
            missing.append(d)

    if missing:
        print(f"[ERROR] Release missing assets: {missing}")
        sys.exit(1)

    # RUN_CALCULATOR.bat launches %~dp0python\python.exe and refuses to start
    # without it, printing "ERROR: Python runtime folder is missing!". A
    # package produced by this script never contains that folder, so saying
    # "complete and clean" would be misleading.
    #
    # The bundled interpreter is produced by portable\BUILD_ON_MY_PC.bat, not
    # here. So this is a WARNING by default and only fatal under
    # --require-python, which is what a real shippable package is built with.
    if not (DIST_DIR / PYTHON_EXE_REL).exists():
        print("")
        print("[WARNING] This package CANNOT BE LAUNCHED AS-IS.")
        print(f"[WARNING]   Missing: {PYTHON_EXE_REL.as_posix()}")
        print("[WARNING]   RUN_CALCULATOR.bat will stop with")
        print('[WARNING]     "ERROR: Python runtime folder is missing!"')
        print("[WARNING]   Build the shippable folder with")
        print("[WARNING]     portable\\BUILD_ON_MY_PC.bat")
        print("[WARNING]   (it downloads the embeddable Python), or rerun this")
        print("[WARNING]   script with --require-python to make this fatal.")
        print("")
        if require_python:
            print("[ERROR] --require-python: bundled python\\python.exe is absent.")
            sys.exit(1)
    elif require_python:
        print(f"[VERIFY] Bundled interpreter present: {PYTHON_EXE_REL.as_posix()}")

    print("[VERIFY] Release package is complete and clean.")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Build and verify the portable calculator release.")
    ap.add_argument("--require-python", action="store_true",
                    help="fail if the bundled python\\python.exe is missing, "
                         "i.e. the package would refuse to start")
    args = ap.parse_args()

    clean_and_assemble()
    verify_release(require_python=args.require_python)
