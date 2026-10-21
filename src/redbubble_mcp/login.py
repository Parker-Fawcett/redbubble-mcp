"""One-time login helper for the persistent Redbubble browser.

Usage: redbubble-mcp-login
Attaches to (or spawns) the detached Redbubble browser window, lets you log in
manually there (captchas stay human), then saves the session snapshot.
"""

from __future__ import annotations

import json
import sys

from redbubble_mcp import browser_session
from redbubble_mcp.guards import DEFAULT_DIR

LOGIN_URL = "https://www.redbubble.com/auth/login"
HOME_URL = "https://www.redbubble.com/"
LOGGED_IN_MARKS = ("Manage portfolio", "Add new work", "Add New Work", "Saved payment")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed. Run: python -m pip install playwright "
            "&& python -m playwright install chromium"
        )
        return 1
    from playwright._impl._errors import TargetClosedError

    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    print("Attaching to (or starting) the persistent Redbubble browser window.")
    print("Log into your account IN THAT WINDOW - captchas stay human.")
    print("(If you close that window by mistake, no problem: press Enter and it relaunches.)")

    browser_session._ensure_chrome()

    with sync_playwright() as p:
        def reconnect():
            browser_session._ensure_chrome()
            browser = p.chromium.connect_over_cdp(browser_session.CDP_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            return browser, context, page

        browser, context, page = reconnect()
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
        except TargetClosedError:
            browser, context, page = reconnect()
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)

        while True:
            try:
                input("Log in inside the window, then press Enter here > ")
            except (EOFError, KeyboardInterrupt):
                print("Aborted - nothing saved.")
                return 1

            try:
                page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
            except TargetClosedError:
                print("The window was closed - relaunching it...")
                browser, context, page = reconnect()
                page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(3_000)
            body = page.evaluate("document.body.innerText.slice(0, 4000)")

            if not any(mark in body for mark in LOGGED_IN_MARKS):
                print(
                    "Doesn't look logged in yet (no artist dashboard detected). "
                    "Finish the login in the window and press Enter again."
                )
                continue

            cookies = context.cookies("https://www.redbubble.com")
            cookie_values = {c["name"]: c["value"] for c in cookies}
            ua = page.evaluate("navigator.userAgent") or ""

            (DEFAULT_DIR / "storage_state.json").write_text(
                json.dumps(
                    {
                        "cookies": cookies,
                        "origins": [],
                        "userAgent": ua,
                    }
                ),
                "utf-8",
            )

            from redbubble_mcp.session import SessionStore

            SessionStore().save_cookies(cookie_values, user_agent=ua)
            print(f"Session captured ({len(cookies)} cookies) -> {DEFAULT_DIR / 'session.json'}")
            print("Done. The Redbubble window stays open; the MCP server will use it.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
