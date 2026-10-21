from redbubble_mcp.session import SessionStore


def test_roundtrip_preserves_cookies(tmp_path):
    store = SessionStore(state_dir=str(tmp_path))
    store.save_cookies(
        {"rbsid": "abc", "__cf_bm": "xyz", "XSRF-TOKEN": "tok%20en"},
        user_agent="TestAgent/1.0",
    )
    reopened = SessionStore(state_dir=str(tmp_path))
    assert reopened.cookie_names() >= {"rbsid", "__cf_bm", "XSRF-TOKEN"}
    assert reopened.user_agent == "TestAgent/1.0"


def test_user_agent_survives_reload(tmp_path):
    store = SessionStore(state_dir=str(tmp_path))
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    store.save_cookies({"a": "1"}, user_agent=ua)
    assert SessionStore(state_dir=str(tmp_path)).user_agent == ua


def test_cookie_header_format(tmp_path):
    store = SessionStore(state_dir=str(tmp_path))
    store.save_cookies({"rbsid": "abc", "b": "2", "a": "1"}, user_agent="UA")
    header = store.cookie_header()
    parts = header.split("; ")
    assert set(parts) == {"rbsid=abc", "b=2", "a=1"}


def test_defaults_when_no_state_file(tmp_path):
    store = SessionStore(state_dir=str(tmp_path))
    header = store.cookie_header()
    assert store.cookie_names() == set()


def test_merge_new_cookies(tmp_path):
    store = SessionStore(state_dir=str(tmp_path))
    store.save_cookies({"a": "1"}, user_agent="UA")
    store.merge_cookies({"a": "9", "b": "2"})
    assert store.cookie_names() >= {"a", "b"}
    assert SessionStore(state_dir=str(tmp_path)).cookies["a"] == "9"
