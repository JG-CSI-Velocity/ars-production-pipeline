"""Tests for style.headline -- scores headlines against SLIDE_MAPPING.md rules."""

from style.headline import HeadlineScore, score_headline


def test_complete_consultative_headline_passes_all_rules():
    text = "Three branches drove 62% of debit growth, led by Main Office at 23%."
    s = score_headline(text)
    assert s.is_complete_sentence is True
    assert s.has_metric is True
    assert s.has_direction is True
    assert s.has_driver_clause is True
    assert s.char_count == len(text)
    assert s.violates == []


def test_fragment_headline_flags_sentence_and_direction():
    text = "Debit Card Performance by Branch"
    s = score_headline(text)
    assert s.is_complete_sentence is False
    assert s.has_direction is False
    assert "not a complete sentence" in " | ".join(s.violates)


def test_metric_without_direction_flagged():
    text = "Debit penetration was 62%."
    s = score_headline(text)
    assert s.has_metric is True
    assert s.has_direction is False
    assert "missing direction word" in " | ".join(s.violates)


def test_direction_without_driver_flagged():
    text = "Interchange revenue rose 14%."
    s = score_headline(text)
    assert s.has_direction is True
    assert s.has_driver_clause is False
    assert "missing driver clause" in " | ".join(s.violates)


def test_long_headline_flagged():
    text = "A " * 80 + "."  # > 120 chars
    s = score_headline(text)
    assert s.char_count > 120
    assert any("too long" in v for v in s.violates)


def test_percent_dollar_and_number_all_count_as_metric():
    assert score_headline("Revenue rose $2.1M due to ICS onboarding.").has_metric
    assert score_headline("Attrition fell 12% driven by campaign.").has_metric
    assert score_headline("247 new accounts opened, led by branch 04.").has_metric
