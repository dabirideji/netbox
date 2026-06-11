"""Tests for macOS helpers."""

from __future__ import annotations

from netbox.util import macos


def test_detect_location_client_prefers_terminal_over_python(monkeypatch) -> None:
    chain = {
        100: ("Python", "python -m netbox", "99"),
        99: ("zsh", "-zsh", "98"),
        98: ("Cursor", "/Applications/Cursor.app/Contents/MacOS/Cursor", "1"),
    }

    def fake_ps_field(pid: int, field: str) -> str:
        if pid not in chain:
            return ""
        command, args, ppid = chain[pid]
        if field == "comm":
            return command
        if field == "args":
            return args
        if field == "ppid":
            return ppid
        return ""

    monkeypatch.setattr(macos, "_ps_field", fake_ps_field)
    monkeypatch.setattr(macos.os, "getpid", lambda: 100)

    assert macos.detect_location_client() == "Cursor"


def test_detect_location_client_returns_none_off_macos(monkeypatch) -> None:
    monkeypatch.setattr(macos.platform, "system", lambda: "Linux")
    assert macos.detect_location_client() is None
