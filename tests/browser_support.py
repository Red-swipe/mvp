"""Resolve an installed Playwright-managed Chromium across platforms."""

import os
import re
import sys
from pathlib import Path


def chromium_executable():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    with sync_playwright() as playwright:
        expected = Path(playwright.chromium.executable_path)
    if expected.is_file():
        return str(expected)

    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if configured and configured != "0":
        browser_root = Path(configured)
    elif sys.platform == "win32":
        browser_root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ms-playwright"
    else:
        browser_root = Path.home() / ".cache" / "ms-playwright"

    if sys.platform == "win32":
        relative_paths = (Path("chrome-win64/chrome.exe"), Path("chrome-win/chrome.exe"))
    elif sys.platform == "darwin":
        relative_paths = (Path("chrome-mac/Chromium.app/Contents/MacOS/Chromium"),)
    else:
        relative_paths = (Path("chrome-linux/chrome"), Path("chrome-linux64/chrome"))

    candidates = []
    for browser_dir in browser_root.glob("chromium-*"):
        match = re.search(r"chromium-(\d+)", browser_dir.name)
        version = int(match.group(1)) if match else -1
        for relative_path in relative_paths:
            executable = browser_dir / relative_path
            if executable.is_file():
                candidates.append((version, executable))

    if not candidates:
        return None
    return str(max(candidates, key=lambda item: item[0])[1])
