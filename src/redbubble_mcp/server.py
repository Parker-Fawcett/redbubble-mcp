"""Redbubble MCP server - tools that let an AI agent act as your print-on-demand
account assistant.

Everything runs through a real headed browser page (Cloudflare defeats plain
HTTP and headless browsers), so expect a Redbubble window to appear while tools
run. Writes are guarded by UploadLedger: 30/day cap + pacing, per Redbubble's ToS."""

from __future__ import annotations

import datetime as dt
import json

from fastmcp import FastMCP

from redbubble_mcp.browser_client import BrowserClient, RBAuthError
from redbubble_mcp.browser_session import get_session, has_session
from redbubble_mcp.guards import UploadLedger
from redbubble_mcp.works import parse_works

mcp = FastMCP(
    "redbubble",
    instructions=(
        "Redbubble assistant for the artist's own account. Prefer the high-level "
        "tools (list_works, get_earnings, get_payment_info, safety_info). "
        "graphql_tool for anything else Redbubble's studio GraphQL schema offers; "
        "upload_work to publish a design. Check safety_info before any write."
    ),
)

EARNINGS_QUERY = (
    "query withEarningsSummary($aggregatedBy: String, $to: String, $from: String, $timezone: String) "
    "{ earningsSummary(aggregatedBy: $aggregatedBy, to: $to, from: $from, timezone: $timezone) "
    "{ currencyIso totalEarnings graphData { x y __typename } __typename } }"
)
PAYMENT_QUERY = (
    "query withUserPaymentInformation "
    "{ artistData: artistAccount_artistData { paymentInformation "
    "{ paymentMethod payability lastPaymentDate nextPaymentDate __typename } __typename } }"
)
WORKS_QUERY = (
    "query withWorks($workIds: [ID!]!, $locale: String!) "
    "{ artistData: artistAccount_artistData { works(ids: $workIds) { ...WorkDetails __typename } __typename } } "
    "fragment WorkDetails on artistAccount_Work { workId title(locale: $locale) "
    "image: studioImage(maxWidth: 160) { url __typename } url(locale: $locale) "
    "publicationState tags(locale: $locale) __typename }"
)


def _client() -> BrowserClient:
    return BrowserClient(page_provider=lambda: get_session().current_page)


@mcp.tool
def safety_info() -> str:
    """Redbubble's bot-automation rules: daily upload cap, pacing, ToS risk summary."""
    return (
        "Redbubble has no official public artist API; this tool uses their interfaces.\n"
        "- Hard limit: 30 uploads/day across all accounts (ToS-enforced).\n"
        "- ToS: automation without written permission can permanently close the account.\n"
        f"- Mitigations here: 30/day cap enforced, {UploadLedger().min_interval_s:.0f}s min between uploads.\n"
        "- Rule of thumb: read freely, write slowly, never bulk-farm."
    )


@mcp.tool
def redbubble_status() -> str:
    """Check whether a saved Redbubble session exists and today's upload budget."""
    today = dt.date.today()
    ledger = UploadLedger()
    return (
        f"saved session: {'yes' if has_session() else 'NO (run: redbubble-mcp-login)'}\n"
        f"uploads today: {ledger.count_on(today)}/30"
    )


@mcp.tool
def list_works() -> str:
    """List every work in your Redbubble portfolio (id, title, edit/duplicate URLs)."""
    page = get_session().current_page
    page.goto("https://www.redbubble.com/portfolio/manage_works", wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(3_000)
    hrefs = page.evaluate(
        "() => Array.from(new Set(Array.from(document.querySelectorAll('a[href]')).map(a => a.href)))"
    )
    return json.dumps(parse_works(hrefs))


@mcp.tool
def get_earnings() -> str:
    """Total earnings + monthly graph for the last 12 months (from Redbubble's studio GraphQL)."""
    today = dt.datetime.now()
    year_ago = today - dt.timedelta(days=365)
    variables = {
        "aggregatedBy": "month",
        "to": today.strftime("%Y-%m-01T00:00:00.000Z"),
        "from": year_ago.strftime("%Y-%m-01T00:00:00.000Z"),
        "timezone": "utc",
    }
    try:
        data = _client().graphql(EARNINGS_QUERY, variables=variables)
        return json.dumps(data)
    except RBAuthError as exc:
        return f"AUTH ERROR: {exc}"


@mcp.tool
def get_payment_info() -> str:
    """Payout info: payment method, payability, last/next payment dates."""
    try:
        return json.dumps(_client().graphql(PAYMENT_QUERY))
    except RBAuthError as exc:
        return f"AUTH ERROR: {exc}"


@mcp.tool
def get_work_details(work_ids: list[int]) -> str:
    """Details for specific works by numeric id (title, tags, publicationState, image url, shop url)."""
    try:
        return json.dumps(_client().graphql(WORKS_QUERY, variables={"workIds": work_ids, "locale": "en"}))
    except RBAuthError as exc:
        return f"AUTH ERROR: {exc}"


@mcp.tool
def graphql_tool(query: str, variables: dict | None = None) -> str:
    """Run any GraphQL query/mutation against Redbubble's studio GraphQL endpoint
    (POST /studio/graphql). READ queries only for discovery; mutations will hit
    the real account. Returns {data: ...}."""
    try:
        return json.dumps(_client().graphql(query, variables=variables))
    except RBAuthError as exc:
        return f"AUTH ERROR: {exc}"


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
    from (format https://www.redbubble.com/portfolio/images/<id>-<slug>) - the
    most reliable, least detectable approach. tags: comma-separated, max 15.
    Enforces 30/day cap + pacing interval."""
    ledger = UploadLedger()
    now = dt.datetime.now()
    try:
        ledger.assert_can_upload(now)
    except Exception as exc:
        return f"BLOCKED: {exc}"

    try:
        from redbubble_mcp.upload_browser import upload_via_browser

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
