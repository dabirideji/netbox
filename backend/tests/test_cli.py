from pathlib import Path

import pytest

from netbox.cli import (
    apply_runtime_target_seeds,
    database_exists,
    ensure_initialized,
    main,
    parse_args,
    resolve_static_dir,
    seed_defaults,
)
from netbox.storage import StatusStore


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


def test_main_seed_command_inserts_bundled_targets(tmp_path: Path) -> None:
    db_path = tmp_path / "netbox.sqlite3"
    assert main(["seed", "--db-path", str(db_path)]) == 0

    store = StatusStore(str(db_path))
    try:
        ids = {target.id for target in store.list_targets()}
        assert "example-website" in ids
    finally:
        store.close()


def test_database_exists_reports_missing_file(tmp_path: Path) -> None:
    db_path = tmp_path / "netbox.sqlite3"

    assert database_exists(str(db_path)) is False

    db_path.write_text("", encoding="utf-8")
    assert database_exists(str(db_path)) is True


def test_ensure_initialized_seeds_missing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "netbox.sqlite3"
    config = parse_args(["--db-path", str(db_path)])

    ensure_initialized(config)

    store = StatusStore(str(db_path))
    try:
        ids = {target.id for target in store.list_targets()}
        assert "example-website" in ids
    finally:
        store.close()


def test_ensure_initialized_is_noop_when_database_exists(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "netbox.sqlite3"
    config = parse_args(["--db-path", str(db_path)])
    assert seed_defaults(config) == 0

    store = StatusStore(str(db_path))
    try:
        assert store.delete_target("example-website")
        before = {target.id for target in store.list_targets()}
    finally:
        store.close()

    ensure_initialized(config)
    captured = capsys.readouterr()

    store = StatusStore(str(db_path))
    try:
        after = {target.id for target in store.list_targets()}
    finally:
        store.close()

    assert "first-time setup" not in captured.out.lower()
    assert after == before
    assert "example-website" not in after


def test_apply_runtime_target_seeds_does_not_restore_deleted_bundled_targets(tmp_path: Path) -> None:
    db_path = tmp_path / "netbox.sqlite3"
    config = parse_args(["--db-path", str(db_path)])

    assert seed_defaults(config) == 0

    store = StatusStore(str(db_path))
    try:
        assert store.delete_target("example-website")
        apply_runtime_target_seeds(config, store, gateway="192.168.1.1")
        ids = {target.id for target in store.list_targets()}
        assert "example-website" not in ids
        assert "gateway" in ids
    finally:
        store.close()


def test_apply_runtime_target_seeds_updates_gateway_when_route_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "netbox.sqlite3"
    config = parse_args(["--db-path", str(db_path)])

    assert seed_defaults(config) == 0

    store = StatusStore(str(db_path))
    try:
        store.update_target("gateway", {"host": "10.10.7.1", "config": {"host": "10.10.7.1"}})
        apply_runtime_target_seeds(config, store, gateway="192.168.18.1")
        gateway = store.get_target("gateway")
        assert gateway is not None
        assert gateway.host == "192.168.18.1"
        assert gateway.config["host"] == "192.168.18.1"
    finally:
        store.close()
