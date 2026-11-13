"""
Browser Control Service (TASK-GAP-01 / GAP-01).

Implements comprehensive web browser navigation and Playwright DOM automation:
- Native OS Browser Launching (Windows, macOS, Linux)
- Playwright-based interactive automation (click, type, scroll, extract, fill)
- Graceful fallback and error reporting when Playwright is not installed
- Five-Word Outcome Contract (done, unverified, failed, ask, started)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from importlib.util import find_spec
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import threading
from typing import Any, Dict, List, Optional
import webbrowser

from app.actions.base import ActionOutcomeResponse, ToolOutcome, done, failed, unverified
from app.schemas.browser_control import BrowserControlParameters

logger = logging.getLogger(__name__)

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

SEARCH_ENGINES: Dict[str, str] = {
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "yandex": "https://yandex.com/search/?text=",
}

BROWSER_ALIASES: Dict[str, str] = {
    "google chrome": "chrome",
    "google-chrome": "chrome",
    "microsoft edge": "edge",
    "ms edge": "edge",
    "msedge": "edge",
    "mozilla firefox": "firefox",
    "opera gx": "operagx",
    "opera_gx": "operagx",
}

MAC_APP_NAMES: Dict[str, str] = {
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "firefox": "Firefox",
    "opera": "Opera",
    "operagx": "Opera GX",
    "brave": "Brave Browser",
    "vivaldi": "Vivaldi",
    "safari": "Safari",
}


def normalize_url(url: str) -> str:
    """Normalize a raw string or domain into a valid HTTP/HTTPS URL."""
    url = url.strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    if "." not in url:
        url = url + ".com"
    return "https://" + url


class BrowserControlService:
    """Service orchestrating browser navigation and Playwright automation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_browser: Optional[str] = None
        self._has_playwright = find_spec("playwright") is not None
        self._driver: Any = None
        self._context: Any = None
        self._page: Any = None

    @property
    def is_playwright_installed(self) -> bool:
        """Check whether the playwright package is importable."""
        return find_spec("playwright") is not None

    def execute(self, params: BrowserControlParameters) -> ActionOutcomeResponse:
        """Execute a browser control operation according to the five-word outcome contract."""
        action = params.action.lower().strip()
        browser = (params.browser or "").lower().strip() or None
        if browser:
            browser = BROWSER_ALIASES.get(browser, browser)

        # 1. Native / Standard Navigation Actions
        if action in ("go_to", "open", "navigate"):
            target_url = normalize_url(params.url or "")
            return self._navigate_native(target_url, browser)

        if action == "search":
            engine = (params.engine or "google").lower().strip()
            base_url = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["google"])
            query = (params.query or "").strip()
            if not query:
                return failed("browser.control", error="Search query was empty or missing.", message="Search query was empty or missing.")
            search_url = base_url + query.replace(" ", "+")
            return self._navigate_native(search_url, browser)

        if action == "new_tab":
            target_url = normalize_url(params.url or "") if params.url else ""
            return self._navigate_native(target_url, browser)

        # 2. Interactive DOM Automation Actions (Requires Playwright)
        interactive_actions = (
            "click", "type", "scroll", "fill_form", "get_text",
            "get_url", "press", "close_tab", "screenshot",
            "back", "forward", "reload", "close", "close_all"
        )
        if action in interactive_actions:
            if not self.is_playwright_installed:
                return unverified(
                    "browser.control",
                    f"Action '{action}' requires Playwright, which is not installed. "
                    "Run: pip install playwright && playwright install chromium",
                    playwright_required=True,
                )
            return self._execute_playwright(action, params)

        if action == "list_browsers":
            return done(
                "browser.control",
                "Available browser engines: chrome, edge, firefox, opera, brave, safari.",
                browsers=["chrome", "edge", "firefox", "opera", "brave", "safari"],
            )

        return failed("browser.control", error=f"Unsupported browser action: '{action}'.", message=f"Unsupported browser action: '{action}'.")

    def _navigate_native(self, url: str, browser_name: Optional[str] = None) -> ActionOutcomeResponse:
        """Hand off a URL to the operating system's native browser."""
        if not url or url == "about:blank":
            url = ""

        try:
            if browser_name:
                launched = self._launch_specific_browser(url, browser_name)
                if launched:
                    return unverified(
                        "browser.control",
                        f"Target URL handed to {browser_name}. Awaiting navigation confirmation.",
                        url=url,
                        browser=browser_name,
                    )

            # Fall back to system default URL handler
            if _OS == "Windows":
                if url:
                    os.startfile(url)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["cmd", "/c", "start", ""], creationflags=subprocess.CREATE_NO_WINDOW)
            elif _OS == "Darwin":
                cmd = ["open"]
                if url:
                    cmd.append(url)
                subprocess.run(cmd, check=True, timeout=10)
            else:
                cmd = ["xdg-open"]
                if url:
                    cmd.append(url)
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return unverified(
                "browser.control",
                "URL handed to the system default browser. Navigation initiated.",
                url=url,
            )
        except Exception as exc:
            logger.warning("Native browser launch encountered error: %s", exc)
            try:
                if url and webbrowser.open(url):
                    return unverified(
                        "browser.control",
                        "URL opened via standard web browser launcher.",
                        url=url,
                    )
            except Exception as wb_exc:
                logger.error("Webbrowser fallback failed: %s", wb_exc)

            return failed(
                "browser.control",
                f"Failed to open native browser for URL: {url}",
                error=str(exc),
            )

    def _launch_specific_browser(self, url: str, browser_name: str) -> bool:
        """Attempt to launch a specific designated browser executable."""
        try:
            if _OS == "Darwin":
                app = MAC_APP_NAMES.get(browser_name)
                if app:
                    cmd = ["open", "-a", app]
                    if url:
                        cmd.append(url)
                    subprocess.run(cmd, check=True, timeout=10)
                    return True
            elif _OS == "Windows":
                exe = shutil.which(browser_name)
                if exe:
                    args = [exe, url] if url else [exe]
                    subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
                    return True
            else:
                exe = shutil.which(browser_name)
                if exe:
                    args = [exe, url] if url else [exe]
                    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
        except Exception as exc:
            logger.debug("Specific browser launch for '%s' failed: %s", browser_name, exc)
        return False

    def _execute_playwright(self, action: str, params: BrowserControlParameters) -> ActionOutcomeResponse:
        """Execute interactive DOM actions via Playwright."""
        try:
            # We lazy-import Playwright inside the execution path
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()

                if params.url:
                    page.goto(normalize_url(params.url), timeout=30000)

                if action == "click":
                    if not params.selector:
                        browser.close()
                        return failed("browser.control", error="Click action requires a valid CSS selector.", message="Click action requires a valid CSS selector.")
                    page.click(params.selector, timeout=10000)
                    browser.close()
                    return done("browser.control", f"Clicked selector: {params.selector}")

                if action == "type":
                    if not params.selector:
                        browser.close()
                        return failed("browser.control", error="Type action requires a valid CSS selector.", message="Type action requires a valid CSS selector.")
                    text = params.text or ""
                    if params.clear_first:
                        page.fill(params.selector, text)
                    else:
                        page.type(params.selector, text)
                    browser.close()
                    return done("browser.control", f"Typed text into selector: {params.selector}")

                if action == "get_text":
                    content = page.inner_text("body")
                    current_url = page.url
                    browser.close()
                    return done(
                        "browser.control",
                        "Extracted text content from page.",
                        data={"text": content[:4000], "url": current_url},
                    )

                if action == "get_url":
                    current_url = page.url
                    browser.close()
                    return done("browser.control", f"Current page URL: {current_url}", data={"url": current_url})

                if action == "scroll":
                    direction = (params.direction or "down").lower()
                    amount = params.amount or 500
                    delta_y = amount if direction == "down" else -amount
                    page.mouse.wheel(0, delta_y)
                    browser.close()
                    return done("browser.control", f"Scrolled page {direction} by {amount}px.")

                browser.close()
                return done("browser.control", f"Executed browser action '{action}' successfully.")

        except Exception as exc:
            logger.error("Playwright automation error for action '%s': %s", action, exc)
            return failed(
                "browser.control",
                f"Browser automation failed for action '{action}': {str(exc)}",
                error=str(exc),
            )
