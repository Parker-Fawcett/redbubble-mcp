import pytest

from redbubble_mcp.works import parse_works

FAKE_HREFS = [
    "https://www.redbubble.com/portfolio/manage_works",
    "https://www.redbubble.com/portfolio/images/162711204-trust-nobody",
    "https://www.redbubble.com/portfolio/images/162711204-trust-nobody/edit",
    "https://www.redbubble.com/portfolio/images/162711204-trust-nobody/duplicate",
    "https://www.redbubble.com/portfolio/images/180660107-reunion-v2",
    "https://www.redbubble.com/portfolio/images/new",
    "https://www.redbubble.com/account/sales",
]


def test_extracts_unique_works_with_id_title_and_slug():
    works = parse_works(FAKE_HREFS)
    assert len(works) == 2
    assert works[0] == {
        "id": "162711204",
        "slug": "trust-nobody",
        "title": "trust nobody",
        "url": "https://www.redbubble.com/portfolio/images/162711204-trust-nobody",
        "edit_url": "https://www.redbubble.com/portfolio/images/162711204-trust-nobody/edit",
        "duplicate_url": "https://www.redbubble.com/portfolio/images/162711204-trust-nobody/duplicate",
    }


def test_ignores_new_edit_duplicate_and_other_pages():
    works = parse_works(FAKE_HREFS)
    assert all(w["slug"] != "new" for w in works)
    assert all(
        not w["url"].endswith(("/edit", "/duplicate")) for w in works
    )


def test_empty_input_returns_empty():
    assert parse_works([]) == []
