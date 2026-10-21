import pytest

from redbubble_mcp.browser_client import BrowserClient, ChallengeError, RBAuthError

QUERY = "query withEarningsSummary { earningsSummary { totalEarnings __typename } __typename }"


class FakePage:
    """Stands in for a playwright page whose evaluate() runs our in-page fetch."""

    def __init__(self, results):
        self.results = list(results)
        self.reloads = 0

    def reload(self):
        self.reloads += 1

    def evaluate(self, code, payload=None):
        return self.results.pop(0)


def test_graphql_returns_data():
    page = FakePage([{"status": 200, "body": '{"data":{"earningsSummary":{"totalEarnings":56.21}}}'}])
    client = BrowserClient(page_provider=lambda: page)
    assert client.graphql(QUERY) == {"earningsSummary": {"totalEarnings": 56.21}}


def test_reloads_once_on_cloudflare_challenge_then_succeeds():
    page = FakePage(
        [
            {"status": 403, "body": "<html>Just a moment...</html>"},
            {"status": 200, "body": '{"data":{"ok":true}}'},
        ]
    )
    client = BrowserClient(page_provider=lambda: page)
    assert client.graphql(QUERY) == {"ok": True}
    assert page.reloads == 1


def test_gives_up_with_auth_error_after_repeated_challenges():
    page = FakePage(
        [
            {"status": 403, "body": "Just a moment..."},
            {"status": 403, "body": "Just a moment..."},
        ]
    )
    client = BrowserClient(page_provider=lambda: page)
    with pytest.raises(RBAuthError) as exc:
        client.graphql(QUERY)
    assert "login" in str(exc.value).lower()


def test_raises_challenge_error_without_retries():
    page = FakePage([{"status": 500, "body": ""}])
    client = BrowserClient(page_provider=lambda: page)
    with pytest.raises(ChallengeError):
        client.graphql(QUERY, max_challenge_retries=0)


def test_graphql_extracts_operation_name_from_typed_queries():
    page = FakePage([{"status": 200, "body": '{"data":{"earningsSummary":{"totalEarnings":1.0}}}'}])
    client = BrowserClient(page_provider=lambda: page)
    client.graphql(
        "query withEarningsSummary($from: String, $to: String) "
        "{ earningsSummary(from: $from, to: $to) { totalEarnings __typename } }"
    )
    sent = client.last_payload
    assert sent["operationName"] == "withEarningsSummary"


def test_fetch_json_passthrough():
    def provider():
        page = FakePage([{"status": 200, "body": '{"a": 1}'}])
        return page

    page = provider()
    client = BrowserClient(page_provider=lambda: page)
    assert client.fetch_json("/typeahead/?locale=en") == {"a": 1}
