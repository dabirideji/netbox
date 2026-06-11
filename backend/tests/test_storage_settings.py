"""Tests for persisted storage retention settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from netbox.storage import StatusStore


def test_storage_settings_defaults_from_config(tmp_path: Path) -> None:
    store = StatusStore(
        tmp_path / "status.sqlite3",
        {
            "autoPrune": True,
            "limits": {
                "maxDatabaseBytes": 5_368_709_120,
                "maxIncidents": 1_000_000,
                "maxPingSamples": 100_000,
                "maxSpeedTests": 500,
            },
        },
    )

    settings = store.get_storage_settings()

    assert settings["autoPrune"] is True
    assert settings["limits"]["maxDatabaseBytes"] == 5_368_709_120
    assert settings["limits"]["maxIncidents"] == 1_000_000
    store.close()


def test_storage_settings_persist_updates(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    updated = store.update_storage_settings(
        {
            "limits": {
                "maxDatabaseBytes": 2_147_483_648,
                "maxIncidents": 250_000,
            }
        }
    )

    assert updated["limits"]["maxDatabaseBytes"] == 2_147_483_648
    assert updated["limits"]["maxIncidents"] == 250_000

    reopened = StatusStore(tmp_path / "status.sqlite3")
    assert reopened.get_storage_settings()["limits"]["maxDatabaseBytes"] == 2_147_483_648
    reopened.close()
    store.close()


def test_storage_settings_patch_rejects_unknown_keys(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    with pytest.raises(ValueError, match="unknown storage settings field"):
        store.update_storage_settings({"autoPrune": True, "extra": 1})
    store.close()
