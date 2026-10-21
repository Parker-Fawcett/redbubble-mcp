"""Browser-backed client for Redbubble.

Site is Cloudflare-protected: plain HTTP (httpx/requests) gets challenged, even
when carrying a valid cookie session, and headless browsers get challenged too.
What works is executing fetches *inside a real, headed browser page* that has
the saved session cookies - so that's what this client does.
"""

from __future__ import annotations

import json
import re

BASE_URL = "https://www.redbubble.com"
LOGIN_HINT = (
    "Session is no longer valid or Cloudflare is challenging us. Run "
    "`redbubble-mcp-login` in a terminal to refresh the saved session, then retry."
)

FETCH_JS = """async (payload) => {
    const r = await fetch(payload.url, {
        method: payload.method,
        headers: {'content-type': 'application/json'},
        credentials: 'include',
        body: payload.method === 'GET' ? undefined : JSON.stringify(payload.body ?? {}),
    });
    const text = await r.text();
    return {status: r.status, body: text.slice(0, 200000)};
}"""


class ChallengeError(Exception):
    """Cloudflare is challenging this request; usually fixed by reloading."""


class RBAuthError(Exception):
    pass


class BrowserClient:
    def __init__(self, *, page_provider, max_challenge_retries: int = 1):
        self.page_provider = page_provider
        self.max_challenge_retries = max_challenge_retries

    def _fetch(self, page, url: str, method: str, body=None):
        return page.evaluate(
            FETCH_JS, {"url": url, "method": method, "body": body}
        )

    def request_json(self, url: str, *, method: str = "GET", body=None, **kw):
        page = self.page_provider()
        attempts = 0
        while True:
            result = self._fetch(page, f"{BASE_URL}{url}" if url.startswith("/") else url, method, body)
            status, text = result["status"], result["body"]
            challenged = status in (401, 403, 503) or "Just a moment" in text
            if not challenged:
                if status >= 400:
                    raise ChallengeError(f"HTTP {status}: {text[:200]}")
                try:
                    return json.loads(text)
                except ValueError as exc:
                    raise ChallengeError(f"non-JSON response: {text[:120]}") from exc
            if attempts >= self.max_challenge_retries:
                raise RBAuthError(LOGIN_HINT)
            attempts += 1
            page.reload()
            
    def fetch_json(self, url: str, **kw):
        return self.request_json(url, method="GET", **kw)

    def graphql(self, query: str, variables: dict | None = None, *, operation_name: str | None = None, **kw):
        name = operation_name or (
            re.match(r"(?:query|mutation)\s+([A-Za-z0-9_]+)", query).group(1)
            if re.match(r"(?:query|mutation)\s+[A-Za-z0-9_]+", query)
            else None
        )
        body = {"query": query, "variables": variables or {}, "operationName": name}
        self.last_payload = body
        data = self.request_json("/studio/graphql", method="POST", body=body, **kw)
        if not isinstance(data, dict) or "data" not in data:
            return data
        return data.get("data", {})
