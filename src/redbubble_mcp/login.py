"""One-time login helper: opens a real browser window, you log into Redbubble
manually (including any captcha), and the session is saved for the MCP server.

Usage: redbubble-mcp-login
"""

from __future__ import annotations

import sys
from urllib.parse import urlparse

from redbubble_mcp.guards import DEFAULT_DIR

LOGIN_URL = "https://www.redbubble.com/auth/login"
LOGGED_IN_HINT = "https://www.redbubble.com/"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run: python -m pip install playwright && python -m playwright install chromium")
        return 1

    print("Opening a browser window - log into your Redbubble account there.")
    print("The window stays open until you log in successfully.")
    print("(There should be nothing sensitive printed, but already logged in? Press Ctrl+C to skip.)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGGED_IN_HINT)
        if "auth/login" in page.url:
            page.goto(LOGIN_URL)

        try:
            page.wait_for_url(lambda url: "auth" not in url and urlparse(url).netloc == "www.redbubble.com", timeout=0)
        except Exception:
            pass
        input("Log in, then press Enter here to save the session > ")

        cookies = [
            {"name": c["name"], "value": c["value"]}
            for c in context.cookies()
            if "redbubble" in c["domain"]
        ]
        if not cookies:
            print("No Redbubble cookies captured - session was NOT saved.")
            return 1
        ua = page.evaluate("navigator.userAgent") or ""
        context.storage_state(path=str(DEFAULT_DIR / "storage_state.json"))

    from redbubble_mcp.session import SessionStore

    SessionStore().save_cookies({c["name"]: c["value"] for c in cookies}, user_agent=ua)
    print(f"Saved {len(cookies)} cookies -> {DEFAULT_DIR / 'session.json'}")
    print("Start the MCP server with: redbubble-mcp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
