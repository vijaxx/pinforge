import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pincopy


def test_extract_json_parses_array_embedded_in_prose():
    text = 'Sure, here you go:\n[{"a": 1}, {"a": 2}]\nHope that helps!'
    assert pincopy.extract_json(text) == [{"a": 1}, {"a": 2}]


def test_extract_json_returns_none_with_no_array():
    assert pincopy.extract_json("no json here at all") is None


def test_extract_json_returns_none_on_malformed_array():
    assert pincopy.extract_json("[{broken json}]") is None


def test_fallback_returns_five_variants():
    variants = pincopy.fallback("Large Print Nature Word Search", 48)
    assert len(variants) == 5
    assert all(set(v.keys()) == {"title", "description"} for v in variants)


def test_fallback_titles_fit_pinterest_length_limit():
    variants = pincopy.fallback("Large Print Nature Word Search", 48)
    for v in variants:
        assert len(v["title"]) <= 100


def test_fallback_strips_boilerplate_from_short_theme_name():
    variants = pincopy.fallback("Large Print Nature Word Search", 48)
    # "nature" (the actual theme) should show up; the generic wrapper words shouldn't
    # dominate every title once stripped down to the short form.
    assert any("nature" in v["title"].lower() for v in variants)
