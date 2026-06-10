from pathlib import Path

import pytest

from netbox.cli import main, parse_args, resolve_static_dir


def test_parse_args_validates_ranges() -> None:
    config = parse_args(["--duration", "2s", "--interval", "500ms", "--timeout", "500ms", "--port", "5000"])

    assert config.duration_ms == 2_000
    assert config.interval_ms == 500
    assert config.timeout_ms == 500
    assert config.port == 5000


def test_parse_args_defaults_to_indefinite_tracking() -> None:
    config = parse_args([])

    assert config.duration_ms is None
    assert config.retention_points == 86_400


def test_parse_args_rejects_unsafe_bind_host() -> None:
    with pytest.raises(ValueError):
        parse_args(["--host", "example.com"])


def test_parse_args_rejects_bad_history_size() -> None:
    with pytest.raises(ValueError):
        parse_args(["--history-points", "999"])


def test_resolve_static_dir_override(tmp_path: Path) -> None:
    assert resolve_static_dir(str(tmp_path)) == tmp_path.resolve()


def test_resolve_static_dir_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_static_dir(str(tmp_path / "missing"))


def test_resolve_static_dir_uses_dev_placeholder_without_dist(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "project"
    dist_dir = project_root / "frontend" / "dist"
    monkeypatch.setattr("netbox.cli.PROJECT_ROOT", project_root)
    monkeypatch.setattr("netbox.cli.DEFAULT_STATIC_DIR", dist_dir)

    dev_static = resolve_static_dir(None, dev_mode=True)

    assert dev_static == project_root / ".dev" / "static"
    assert (dev_static / "index.html").is_file()


def test_main_returns_configuration_error_for_invalid_args() -> None:
    assert main(["--duration", "1ms"]) == 2
