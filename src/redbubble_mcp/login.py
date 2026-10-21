"""One-time login helper: opens a real browser window, you log into Redbubble
manually (including any captcha), and the session is saved for the MCP server.

Usage: redbubble-mcp-login
"""

from __future__ import annotations

import sys

from redbubble_mcp.guards import DEFAULT_DIR

LOGIN_URL = "https://www.redbubble.com/auth/login"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run: python -m pip install playwright && python -m playwright install chromium")
        return 1

    DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    print("Opening a browser window - log into your Redbubble account there.")
    print("The window stays open until you log in successfully.")
    print("(There should be nothing sensitive printed, but already logged in? Press Ctrl+C to skip.)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGIN_URL)

        while True:
            try:
                input("Log in, then press Enter here to save the session > ")
            except EOFError:
                return 1

            redbubble_cookies = [
                {"name": c["name"], "value": c["value"]}
                for c in context.cookies()
                if "redbubble" in c["domain"]
            ]
            if len(redbubble_cookies) < 3:
                print(
                    f"Only {len(redbubble_cookies)} Redbubble cookies so far - "
                    "you probably aren't logged in yet. Log in, then press Enter again."
                )
                continue

            ua = page.evaluate("navigator.userAgent") or ""
            context.storage_state(path=str(DEFAULT_DIR / "storage_state.json"))
            break

    from redbubble_mcp.session import SessionStore

    SessionStore().save_cookies(
        {c["name"]: c["value"] for c in redbubble_cookies}, user_agent=ua
    )
    print(f"Saved {len(redbubble_cookies)} cookies -> {DEFAULT_DIR / 'session.json'}")
    print("Start the MCP server with: redbubble-mcp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
