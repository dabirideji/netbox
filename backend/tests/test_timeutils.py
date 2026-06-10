import pytest

from netbox.timeutils import format_duration, parse_duration


def test_parse_duration_units() -> None:
    assert parse_duration("900ms") == 900
    assert parse_duration("2s") == 2_000
    assert parse_duration("1.5m") == 90_000
    assert parse_duration("2h") == 7_200_000


def test_parse_duration_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        parse_duration("soon")


def test_format_duration() -> None:
    assert format_duration(999) == "1s"
    assert format_duration(61_000) == "1m 1s"
    assert format_duration(3_661_000) == "1h 1m 1s"
