"""Tests for the template placeholder registry."""

from __future__ import annotations

import pytest

from placeholders import (
    PLACEHOLDERS,
    Placeholder,
    get_placeholder,
    render,
)


def test_required_placeholders_exist():
    required = {
        "CLIENT_NAME",
        "NOTEBOOK_PENETRATION",
        "PIPELINE_DCTR",
        "ADDRESSABLE_SPEND_USD",
        "NONUSER_COUNT",
        "CLIMBER_COUNT",
        "DECLINER_COUNT",
        "MOST_RECENT_MAILER_MONTH",
    }
    assert required <= set(PLACEHOLDERS.keys())


def test_get_placeholder_returns_dataclass():
    p = get_placeholder("CLIENT_NAME")
    assert isinstance(p, Placeholder)
    assert p.key == "CLIENT_NAME"
    assert p.fake_value  # every placeholder has a fake default


def test_get_placeholder_unknown_raises():
    with pytest.raises(KeyError):
        get_placeholder("NOT_A_REAL_KEY")


def test_render_substitutes_fake_values():
    text = "{{CLIENT_NAME}} has {{NOTEBOOK_PENETRATION}} debit penetration."
    out = render(text)
    assert "{{CLIENT_NAME}}" not in out
    assert "{{NOTEBOOK_PENETRATION}}" not in out


def test_render_accepts_overrides():
    text = "Hello {{CLIENT_NAME}}"
    out = render(text, overrides={"CLIENT_NAME": "First National"})
    assert out == "Hello First National"


def test_render_leaves_unknown_tokens_alone():
    text = "This has {{UNKNOWN_TOKEN}} in it."
    out = render(text)
    assert "{{UNKNOWN_TOKEN}}" in out  # untouched, not an error
