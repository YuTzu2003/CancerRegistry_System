"""Monitoring-indicator report export with a dedicated Playwright runtime resolver."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from modules.blueprint.dashboard.export_report import generate_export_files as _generate_export_files


_PLAYWRIGHT_ENV_LOCK = threading.Lock()
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _contains_chromium(browser_root: Path) -> bool:
    if not browser_root.is_dir():
        return False
    return any(browser_root.glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"))


def _resolve_playwright_browsers_path() -> Path | None:
    candidates = [
        _PROJECT_ROOT / "tasks" / "playwright-browsers",
        Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright",
        Path.home() / "AppData" / "Local" / "ms-playwright",
    ]
    return next((candidate for candidate in candidates if _contains_chromium(candidate)), None)


def generate_indicator_export_files(format_pdf, format_word, charts_data, output_dir):
    """Generate monitoring exports without depending on the annual-report browser path."""
    if not format_pdf and not format_word:
        return _generate_export_files(
            format_pdf, format_word, charts_data, output_dir, "zh-TW", "indicators_report"
        )

    browser_root = _resolve_playwright_browsers_path()
    if browser_root is None:
        raise RuntimeError(
            "找不到匯出預覽所需的 Chromium。請執行："
            ".venv\\Scripts\\python.exe -m playwright install chromium"
        )

    with _PLAYWRIGHT_ENV_LOCK:
        previous = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_root)
        try:
            return _generate_export_files(
                format_pdf, format_word, charts_data, output_dir, "zh-TW", "indicators_report"
            )
        finally:
            if previous is None:
                os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            else:
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = previous
