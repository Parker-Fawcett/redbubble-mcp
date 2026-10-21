"""Keeps one headed browser (with your saved session) alive for the MCP server.

Cloudflare only lets us run fetches through a real page, so all API traffic is
executed from this page's JS context. The window is visible on purpose -
headless Chromium gets challenged, and it doubles as a live look at the account.
"""

from __future__ import annotations

import threading

from redbubble_mcp.guards import DEFAULT_DIR
from redbubble_mcp.session import SessionStore

STUDIO_URL = "https://www.redbubble.com/studio/dashboard"

_lock = threading.Lock()
_instance = None


class MissingSession(Exception):
    pass


class BrowserSession:
    def __init__(self):
        self.page = None
        self.context = None
        self.browser = None

    def _start(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        state_path = DEFAULT_DIR / "storage_state.json"
        self._state_path = state_path
        if not state_path.exists():
            raise MissingSession(
                "No saved browser session. Run `redbubble-mcp-login` first."
            )
        self.browser = self._pw.chromium.launch(headless=False)
        self.context = self.browser.new_context(storage_state=str(state_path))
        page = self.context.new_page()
        page.goto(STUDIO_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3_000)
        self.page = page

    @property
    def current_page(self):
        with _lock:
            if self.page is None:
                self._start()
            return self.page

    def refresh_state(self) -> None:
        if self.context is not None:
            self.context.storage_state(path=str(self._state_path))

    def close(self) -> None:
        try:
            self.refresh_state()
        except Exception:
            pass
        if self.browser is not None:
            self.browser.close()
        try:
            self._pw.stop()
        except Exception:
            pass
        global _instance
        _instance = None


def get_session() -> BrowserSession:
    global _instance
    with _lock:
        if _instance is None:
            _instance = BrowserSession()
        return _instance


def has_session() -> bool:
    return (DEFAULT_DIR / "storage_state.json").exists()
