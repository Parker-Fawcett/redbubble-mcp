"""Redbubble MCP server - tools that let an AI agent act as your print-on-demand
account assistant: session status, generic API discovery against Redbubble's own
web API, and guarded design uploads.

All writes go through the UploadLedger guard (30/day cap + pacing) because
Redbubble's ToS permits permanent bans for automated abuse."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from fastmcp import FastMCP

from redbubble_mcp.client import BASE_URL, RBAuthError, RedbubbleClient
from redbubble_mcp.guards import UploadLedger
from redbubble_mcp.session import SessionStore

mcp = FastMCP(
    "redbubble",
    instructions=(
        "Assistant tools for the artist's own Redbubble account. Use redbubble_get "
        "for read-only API discovery, redbubble_post sparingly for writes, and "
        "upload_work to publish a design file. Check safety_info before any write."
    ),
)


def _client() -> RedbubbleClient:
    store = SessionStore()
    http = __import__("httpx").Client()
    client = RedbubbleClient(http=http, session_store=store)
    client.base_url = BASE_URL
    return client


def _ledger() -> UploadLedger:
    return UploadLedger()


@mcp.tool
def safety_info() -> str:
    """Redbubble's bot-automation rules: daily upload cap, pacing, ToS risk summary."""
    return (
        "Redbubble has no official public artist API; this tool uses their internal web API.\n"
        "- Hard limit: 30 uploads/day across all accounts (ToS-enforced).\n"
        "- ToS: automation without written permission can permanently close the account.\n"
        "- Mitigations built in here: 30/day cap enforced, minimum "
        f"{_ledger().min_interval_s:.0f}s between uploads, personal use only.\n"
        "- Rule of thumb for the agent: read freely, write slowly, never bulk-farm."
    )


@mcp.tool
def redbubble_status() -> str:
    """Check whether a saved Redbubble session exists and today's upload budget."""
    store = SessionStore()
    ledger = _ledger()
    today = dt.date.today()
    cookies = store.cookie_names()
    lines = [
        f"session: {'saved' if store.cookies else 'MISSING (run: redbubble-mcp-login)'}",
        f"cookies: {len(cookies)} stored",
        f"xsrf token: {'yes' if store.xsrf_token() else 'no'}",
        (
            f"user_agent: {store.user_agent[:60]}..."
            if store.user_agent
            else "user_agent: none"
        ),
        f"uploads today: {ledger.count_on(today)}/30",
    ]
    return "\n".join(lines)


@mcp.tool
def redbubble_get(path: str, params: dict | None = None) -> str:
    """GET any Redbubble internal-API path (e.g. /api/v2/...). Returns JSON text.
    Endpoints are undocumented - discover them live via your browser's devtools or
    by probing reasonable paths. Read-only."""
    client = _client()
    try:
        data = client.api_get(path, params=params)
        return json.dumps(data)
    except RBAuthError as exc:
        return f"AUTH ERROR: {exc}"
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool
def redbubble_post(path: str, payload: dict | None = None) -> str:
    """POST to a Redbubble internal-API path. This WRITES to the account - use
    sparingly, only for the owner's own account, and check safety_info first."""
    ledger = _ledger()
    status = safety_info()
    client = _client()
    try:
        data = client.api_post(path, json=payload or {})
        return json.dumps(data)
    except RBAuthError as exc:
        return f"AUTH ERROR: {exc}"
    except Exception as exc:
        return f"ERROR: {exc}. {status}"


@mcp.tool
def upload_work(
    image_path: str,
    title: str,
    tags: str,
    template_work_url: str | None = None,
    description: str = "",
) -> str:
    """Upload a design file to Redbubble using a real browser session.

    template_work_url: URL of one of your existing works to copy product settings
    from (Recommended, format https://www.redbubble.com/portfolio/images/<id>-<slug>).
    If omitted, starts from the default Add New Work page.

    tags: comma-separated, max 15. Enforces 30/day cap + pacing interval."""
    ledger = _ledger()
    now = dt.datetime.now()
    try:
        ledger.assert_can_upload(now)
    except Exception as exc:
        return f"BLOCKED: {exc}"

    from redbubble_mcp.upload_browser import upload_via_browser

    try:
        result = upload_via_browser(
            image_path=image_path,
            title=title,
            tags=tags,
            description=description,
            template_work_url=template_work_url,
        )
    except Exception as exc:
        return f"ERROR: {exc}"

    if result.get("status") == "submitted":
        ledger.record_upload(now)
    return json.dumps(result)


def main():
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
