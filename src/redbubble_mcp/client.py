"""HTTP client for Redbubble's own web API (the one its frontend uses), authenticated with
cookies captured by `redbubble-mcp-login`. Endpoints are undocumented; tools expose generic
api_get/api_post so agents can discover paths live against a real account."""

from __future__ import annotations

import httpx

from redbubble_mcp.session import SessionStore

BASE_URL = "https://www.redbubble.com"

LOGIN_HINT = (
    "Session is no longer valid. Run `redbubble-mcp-login` in a terminal to "
    "log into Redbubble in a browser window, then try again."
)


class RBAuthError(Exception):
    """Raised when Redbubble rejects our stored session."""


class RedbubbleClient:
    def __init__(
        self,
        *,
        http: httpx.Client,
        session_store: SessionStore,
        base_url: str = BASE_URL,
        max_auth_retries: int = 1,
    ):
        self.http = http
        self.session_store = session_store
        self.base_url = base_url
        self.max_auth_retries = max_auth_retries

    # -- headers ----------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "User-Agent": self.session_store.user_agent or DEFAULT_USER_AGENT,
            "Cookie": self.session_store.cookie_header(),
            "Accept": "application/json",
        }
        token = self.session_store.xsrf_token()
        if token:
            headers["X-XSRF-TOKEN"] = token
        return headers

    # -- session refresh -------------------------------------------
    def _refresh_session(self) -> None:
        resp = self.http.get("/", headers=self._headers(), follow_redirects=True)
        resp.raise_for_status()
        self.session_store.merge_cookies(dict(resp.cookies))

    # -- requests ---------------------------------------------------
    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        auth_attempts = 0
        while True:
            resp = self.http.request(
                method, path, headers=self._headers(), follow_redirects=True, **kwargs
            )
            if resp.status_code in (401, 403) and auth_attempts < self.max_auth_retries:
                auth_attempts += 1
                self._refresh_session()
                continue
            if resp.status_code in (401, 403):
                raise RBAuthError(LOGIN_HINT)
            return resp

    def api_get(self, path: str, params: dict | None = None):
        resp = self.request("GET", path, params=params)
        resp.raise_for_status()
        return resp.json()

    def api_post(self, path: str, *, json: dict | None = None, data=None):
        resp = self.request("POST", path, json=json, data=data)
        resp.raise_for_status()
        return resp.json()


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
