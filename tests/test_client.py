import httpx
import pytest

from redbubble_mcp.client import RBAuthError, RedbubbleClient
from redbubble_mcp.session import SessionStore


def make_client(tmp_path, handler):
    store = SessionStore(state_dir=str(tmp_path))
    store.save_cookies({"XSRF-TOKEN": "plain%20token"}, user_agent="UA")
    http = httpx.Client(
        base_url="https://www.redbubble.com",
        transport=httpx.MockTransport(handler),
    )
    return RedbubbleClient(http=http, session_store=store)


def test_xsrf_header_is_sent_from_cookie(tmp_path):
    seen = {}

    def handler(request):
        seen["header"] = request.headers.get("x-xsrf-token")
        return httpx.Response(200, json={"ok": True})

    client = make_client(tmp_path, handler)
    client.api_get("/api/v2/whatever")
    # cookie value is URL-encoded; header must be the decoded form
    assert seen["header"] == "plain token"


def test_retries_once_after_401_then_succeeds(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if request.url.path == "/":
            return httpx.Response(200)  # session refresh hit
        if calls["n"] < 2:
            return httpx.Response(401)
        return httpx.Response(200, json={"works": []})

    client = make_client(tmp_path, handler)
    data = client.api_get("/api/v2/creators/works")
    assert data == {"works": []}
    # 2 work calls (401 + successful retry) + 1 mid-flight session refresh
    assert calls["n"] == 3


def test_raises_actionable_auth_error_after_repeat_401(tmp_path):
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(200)
        return httpx.Response(401, json={"message": "unauthorized"})

    client = make_client(tmp_path, handler)
    with pytest.raises(RBAuthError) as exc:
        client.api_get("/api/v2/creators/works")
    assert "login" in str(exc.value).lower()


def test_post_sends_xsrf_header_too(tmp_path):
    seen = {}

    def handler(request):
        seen["header"] = request.headers.get("x-xsrf-token")
        return httpx.Response(200, json={"id": 1})

    client = make_client(tmp_path, handler)
    client.api_post("/api/v2/creators/works", json={"title": "x"})
    assert seen["header"] == "plain token"
    assert seen["header"] is not None
