#!/usr/bin/env python3
"""Assemble the allowlisted ClassWiz runtime and create its release ZIP."""

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DIST_ROOT = ROOT_DIR / "dist"
DIST_DIR = DIST_ROOT / "calculator_portable"
ZIP_PATH = DIST_ROOT / "calculator_portable.zip"

# Source path -> path inside the extracted calculator_portable directory.
RELEASE_FILES = {
    "README.md": "README.md",
    "main.py": "main.py",
    "mvp_server.py": "mvp_server.py",
    "frontend.html": "frontend.html",
    "portable/RUN_CALCULATOR.bat": "RUN_CALCULATOR.bat",
    "portable/launcher.py": "launcher.py",
    "portable/README_FOR_TEACHER.txt": "README_FOR_TEACHER.txt",
}
RELEASE_DIRS = ("engine", "katex", "ClassWizFontSet", "qrcode")
PYTHON_EXE_REL = Path("python") / "python.exe"


def _ignore_generated(_directory, names):
    return [name for name in names if name == "__pycache__" or name.endswith((".pyc", ".pyo"))]


def _configure_embedded_python(python_dir):
    pth_files = sorted(python_dir.glob("python*._pth"))
    if not pth_files:
        raise FileNotFoundError(f"No python*._pth file found in {python_dir}")
    pth_files[0].write_text(
        "python312.zip\n.\n..\n\n# Uncomment to run site.main() automatically\n#import site\n",
        encoding="ascii",
        newline="\n",
    )


def _copy_release(python_runtime=None):
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    missing = []
    for source_rel, dest_rel in RELEASE_FILES.items():
        source = ROOT_DIR / source_rel
        if not source.is_file():
            missing.append(source_rel)
            continue
        destination = DIST_DIR / dest_rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for directory in RELEASE_DIRS:
        source = ROOT_DIR / directory
        if not source.is_dir():
            missing.append(directory + "/")
            continue
        shutil.copytree(source, DIST_DIR / directory, ignore=_ignore_generated)

    if missing:
        raise FileNotFoundError("Missing allowlisted release paths: " + ", ".join(missing))

    if python_runtime:
        runtime = Path(python_runtime).resolve()
        if not (runtime / "python.exe").is_file():
            raise FileNotFoundError(f"Bundled runtime has no python.exe: {runtime}")
        target = DIST_DIR / "python"
        shutil.copytree(runtime, target, ignore=_ignore_generated)
        _configure_embedded_python(target)


def verify_release(require_python=False):
    missing = [
        destination
        for destination in RELEASE_FILES.values()
        if not (DIST_DIR / destination).is_file()
    ]
    missing.extend(
        directory + "/" for directory in RELEASE_DIRS
        if not (DIST_DIR / directory).is_dir()
    )
    if missing:
        raise FileNotFoundError("Release is incomplete: " + ", ".join(missing))

    bundled_python = DIST_DIR / PYTHON_EXE_REL
    if require_python and not bundled_python.is_file():
        raise FileNotFoundError("A bundled python/python.exe is required for this build")

    forbidden = {"audit", "docs", "tests", "scripts", ".git"}
    present_forbidden = sorted({part for path in DIST_DIR.rglob("*") for part in path.relative_to(DIST_DIR).parts if part in forbidden})
    if present_forbidden:
        raise RuntimeError("Development-only content entered the release: " + ", ".join(present_forbidden))

    if bundled_python.is_file():
        check = subprocess.run(
            [str(bundled_python), "-c", "import engine, mvp_server; mvp_server.run_startup_selftest()"],
            cwd=DIST_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if check.returncode:
            raise RuntimeError("Bundled Python self-test failed:\n" + check.stdout + check.stderr)

    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in DIST_DIR.rglob("*") if path.is_file()):
            archive_name = Path("calculator_portable") / file_path.relative_to(DIST_DIR)
            archive.write(file_path, archive_name.as_posix())

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = set(archive.namelist())
    expected_prefix = "calculator_portable/"
    if not names or any(not name.startswith(expected_prefix) for name in names):
        raise RuntimeError("ZIP contains paths outside calculator_portable/")
    if any(any(part in forbidden for part in Path(name).parts) for name in names):
        raise RuntimeError("ZIP includes development-only content")

    print(f"[VERIFY] Allowlisted runtime files: {len(names)}")
    print(f"[VERIFY] Bundled Python: {'yes' if bundled_python.is_file() else 'no (system Python required)'}")
    print(f"[BUILD] Release ZIP: {ZIP_PATH}")
    print("[VERIFY] Release ZIP is complete and contains no development tree.")
    return ZIP_PATH


def build_release(python_runtime=None, require_python=False):
    _copy_release(python_runtime)
    return verify_release(require_python=require_python)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python-runtime",
        help="directory containing an embeddable Python runtime to include in the ZIP",
    )
    parser.add_argument(
        "--require-python",
        action="store_true",
        help="fail unless the ZIP contains python/python.exe",
    )
    args = parser.parse_args()
    try:
        build_release(args.python_runtime, args.require_python)
    except Exception as exc:
        print(f"[ERROR] Release build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
