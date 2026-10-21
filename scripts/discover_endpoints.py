"""Discover Redbubble's internal API endpoints by loading studio pages with a
saved session and logging every XHR the frontend makes.

Usage (after `redbubble-mcp-login`):
    python scripts/discover_endpoints.py > endpoints.json

Outputs JSON: [{"method": ..., "url": ..., "status": ...}, ...] for any request
to paths containing "/api". Point it at more pages by editing PAGES.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redbubble_mcp.guards import DEFAULT_DIR

PAGES = [
    "https://www.redbubble.com/studio/dashboard",
    "https://www.redbubble.com/account/sales",
    "https://www.redbubble.com/portfolio/manage_works",
]


def main() -> None:
    from playwright.sync_api import sync_playwright

    state_path = DEFAULT_DIR / "storage_state.json"
    if not state_path.exists():
        print("No session. Run: redbubble-mcp-login", file=sys.stderr)
        sys.exit(1)

    seen: dict[tuple, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()

        def on_response(resp):
            url = resp.url
            if "/api" in url and "redbubble" in url:
                key = (resp.request.method, url.split("?")[0])
                seen.setdefault(
                    key, {"method": resp.request.method, "url": url, "status": resp.status}
                )

        page.on("response", on_response)
        for url in PAGES:
            print(f"loading {url} ...", file=sys.stderr)
            try:
                page.goto(url, wait_until="networkidle", timeout=60_000)
            except Exception as exc:
                print(f"skipping {url}: {exc}", file=sys.stderr)
        context.storage_state(path=str(state_path))
        browser.close()

    print(json.dumps(list(seen.values()), indent=2))


if __name__ == "__main__":
    main()
