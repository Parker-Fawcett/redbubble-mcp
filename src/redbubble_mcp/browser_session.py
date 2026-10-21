"""Keeps one headed, detached Chromium webpage-session alive for the MCP server.

Architecture: Chromium runs as an independent process with
--remote-debugging-port + its own profile dir under ~/.redbubble-mcp, so it
survives script exits and keeps Cloudflare/Turnstile cookies warm. Consumers
attach over CDP via playwright.chromium.connect_over_cdp.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from redbubble_mcp.guards import DEFAULT_DIR

CDP_PORT = 9333
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
PROFILE_DIR = DEFAULT_DIR / "browser-profile"
STUDIO_URL = "https://www.redbubble.com/studio/dashboard"

_lock = threading.Lock()
_instance = None


class MissingSession(Exception):
    pass


def _chrome_path() -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        return p.chromium.executable_path


def _cdp_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2) as resp:
            return bool(json.loads(resp.read()))
    except Exception:
        return False


def _spawn_chrome() -> None:
    exe = _chrome_path()
    args = [
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        STUDIO_URL,
    ]
    subprocess.Popen([exe, *args], creationflags=subprocess.CREATE_NO_WINDOW)


class BrowserSession:
    def __init__(self):
        self.page = None
        self.context = None
        self.browser = None

def _ensure_chrome() -> None:
    if _cdp_alive():
        return
    _spawn_chrome()
    deadline = time.time() + 60
    while not _cdp_alive() and time.time() < deadline:
        time.sleep(1)
    if not _cdp_alive():
        raise RuntimeError("could not start Redbubble browser")

    def _start(self):
        from playwright.sync_api import sync_playwright

        state_path = DEFAULT_DIR / "storage_state.json"
        if not state_path.exists():
            raise MissingSession(
                "No saved browser session. Run `redbubble-mcp-login` first."
            )

        _ensure_chrome()
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(CDP_URL)
        self.context = self.browser.contexts[0]

        # first attach: migrate saved session cookies into the CDP profile
        if not self.context.cookies("https://www.redbubble.com"):
            session = json.loads(state_path.read_text("utf-8"))
            cookies = [
                {"name": k, "value": v, "domain": ".redbubble.com", "path": "/"}
                for k, v in session.get("cookies", {}).items()
            ]
            self.context.add_cookies(cookies)

        page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page = page

    @property
    def current_page(self):
        with _lock:
            if self.page is None:
                self._start()
            return self.page

    def refresh_state(self) -> None:
        """Persist cookies from the live browser back to session.json."""
        try:
            if self.context is None:
                return
            cookies = self.context.cookies("https://www.redbubble.com")
            store = {}
            for c in cookies:
                store[c["name"]] = c["value"]
            (DEFAULT_DIR / "session.json").write_text(
                json.dumps({"cookies": store, "user_agent": ""}), "utf-8"
            )
        except Exception:
            pass

    def close(self) -> None:
        self.refresh_state()
        self.page = None
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
