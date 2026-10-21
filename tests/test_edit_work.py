import pytest

from redbubble_mcp.edit_work import normalize_tags


def test_splits_trims_and_dedupes():
    assert normalize_tags(" cat , dog , cat,  bird ") == "cat, dog, bird"


def test_caps_at_15_tags():
    tags = ", ".join(f"t{i}" for i in range(20))
    assert len(normalize_tags(tags).split(", ")) == 15


def test_caps_each_tag_at_50_chars():
    long_tag = "x" * 80
    assert len(normalize_tags(long_tag)) == 50


def test_ignores_empty_fragments():
    assert normalize_tags(", ,cat,,") == "cat"


def test_case_preserved():
    assert normalize_tags("Kawaii Drink") == "Kawaii Drink"
