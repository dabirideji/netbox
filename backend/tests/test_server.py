from pathlib import Path

import pytest

from netbox.server import StatusServer, is_within, parse_query


def test_is_within_accepts_child_path(tmp_path: Path) -> None:
    child = tmp_path / "index.html"
    child.write_text("ok")

    assert is_within(child.resolve(), tmp_path.resolve())


def test_is_within_rejects_parent_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.html"

    assert not is_within(outside.resolve(), tmp_path.resolve())


def test_status_server_suppresses_client_reset_tracebacks(capsys) -> None:
    server = object.__new__(StatusServer)

    try:
        raise ConnectionResetError("client went away")
    except ConnectionResetError:
        server.handle_error(object(), ("127.0.0.1", 62496))

    assert capsys.readouterr().err == ""


def test_parse_query_accepts_bounded_date_range() -> None:
    assert parse_query("from=1000&to=2000&points=25&limit=10") == {
        "from": 1000,
        "to": 2000,
        "points": 25,
        "limit": 10,
        "offset": 0,
    }


def test_parse_query_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="from must be less than or equal to to"):
        parse_query("from=2000&to=1000")
