"""Security-focused regression tests for validation and SQL safety."""

from __future__ import annotations

import ast
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from netbox.core.models import MonitorConfig, NetworkIdentity, Target
from netbox.server import StatusHandler, StatusServer
from netbox.monitor.state import MonitorState
from netbox.storage import StatusStore
from netbox.targets import normalize_target_payload
from netbox.util.http_headers import validate_http_headers
from netbox.util.json_schema import validate_json_schema

STORAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "netbox" / "storage"
SAFE_EXECUTE_FSTRING_NAMES = frozenset(
    {
        "table",
        "order_by",
        "where_sql",
        "time_sql",
        "prefix",
        "column",
    }
)


def _monitor_config(db_path: Path) -> MonitorConfig:
    return MonitorConfig(
        duration_ms=10_000,
        interval_ms=1_000,
        timeout_ms=900,
        port=0,
        host="127.0.0.1",
        latency_warn_ms=100,
        failures_to_degrade=1,
        failures_to_down=2,
        high_latency_to_degrade=1,
        recent_window=5,
        history_points=5,
        retention_points=10,
        no_clear=True,
        wifi_name="",
        db_path=str(db_path),
    )


def _fstring_identifier_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.JoinedStr):
        for part in node.values:
            if isinstance(part, ast.FormattedValue):
                if isinstance(part.value, ast.Name):
                    names.add(part.value.id)
                else:
                    names.add(ast.unparse(part.value))
    return names


def _execute_sql_arg_names(tree: ast.AST) -> list[set[str]]:
    found: list[set[str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in {"execute", "executemany"}:
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.JoinedStr):
            found.append(_fstring_identifier_names(first_arg))
    return found


def test_storage_execute_fstrings_only_use_safe_identifiers() -> None:
    offenders: list[str] = []
    for path in sorted(STORAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for names in _execute_sql_arg_names(tree):
            unsafe = names - SAFE_EXECUTE_FSTRING_NAMES
            if unsafe:
                offenders.append(f"{path.name}: {sorted(unsafe)}")
    assert offenders == []


def test_build_time_filter_callers_use_literal_columns() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "netbox"
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Name)
                and func.id == "build_time_filter"
                or isinstance(func, ast.Attribute)
                and func.attr == "build_time_filter"
            ):
                continue
            if not node.args:
                continue
            column_arg = node.args[0]
            if not isinstance(column_arg, ast.Constant) or not isinstance(column_arg.value, str):
                offenders.append(f"{path.relative_to(root)}:{node.lineno}")
    assert offenders == []


def test_target_id_sql_injection_is_treated_as_literal_parameter(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    store.create_target(
        {
            "id": "gateway",
            "label": "Gateway",
            "host": "127.0.0.1",
            "scope": "gateway",
            "type": "host",
            "protocol": "icmp",
            "group": "Default",
            "environment": "local",
            "enabled": True,
            "intervalMs": 1000,
            "timeoutMs": 900,
            "config": {},
        }
    )

    malicious = "gateway' OR '1'='1"
    assert store.get_target(malicious) is None
    store.close()


def test_api_target_results_rejects_sql_injection_attempt(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'></div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(_monitor_config(tmp_path / "unused.sqlite3"), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        malicious = "gateway'%20OR%201=1--"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/targets/{malicious}/results", timeout=3)
        assert exc_info.value.code == 400
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()


def test_preferences_patch_rejects_unknown_keys(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    with pytest.raises(ValueError, match="unknown preference key"):
        store.update_preferences({"unexpected": True})
    store.close()


def test_preferences_patch_validates_types(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    with pytest.raises(ValueError, match="invalid value for event_page"):
        store.update_preferences({"event_page": "not-a-number"})
    store.close()


def test_preferences_patch_accepts_known_shape(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    merged = store.update_preferences(
        {
            "event_page": 2,
            "timeline_range": {"from": "2026-01-01T00:00", "to": "2026-01-02T00:00"},
        }
    )
    assert merged["event_page"] == 2
    store.close()


def test_storage_settings_patch_rejects_unknown_keys(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    with pytest.raises(ValueError, match="unknown storage settings field"):
        store.update_storage_settings({"autoPrune": True, "extra": 1})
    store.close()


def test_platform_settings_patch_rejects_unknown_keys(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    with pytest.raises(ValueError, match="unknown platform settings field"):
        store.update_platform_settings({"alerts": {"defaultSound": True}, "extra": 1})
    store.close()


def test_platform_settings_patch_rejects_unknown_alert_fields(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")
    with pytest.raises(ValueError, match="unknown platform settings field"):
        store.update_platform_settings({"alerts": {"defaultSound": True, "evil": True}})
    store.close()


def test_validate_json_schema_rejects_empty_patch() -> None:
    with pytest.raises(ValueError, match="at least one preference field is required"):
        validate_json_schema("ui-preferences.patch", {})


def test_http_headers_reject_control_characters_and_invalid_names() -> None:
    with pytest.raises(ValueError, match="invalid header name"):
        validate_http_headers({"Bad Header": "ok"})

    with pytest.raises(ValueError, match="control characters"):
        validate_http_headers({"X-Test": "value\r\nInjected: true"})

    with pytest.raises(ValueError, match="at most 20"):
        validate_http_headers({f"X-{index}": "ok" for index in range(21)})


def test_http_headers_normalize_valid_values() -> None:
    assert validate_http_headers({"Authorization": "Bearer token", "X-Custom": "1"}) == {
        "Authorization": "Bearer token",
        "X-Custom": "1",
    }


def test_target_config_rejects_invalid_http_headers() -> None:
    with pytest.raises(ValueError, match="invalid header name"):
        normalize_target_payload(
            {
                "label": "API",
                "host": "example.com",
                "scope": "external",
                "type": "api",
                "protocol": "https",
                "config": {
                    "url": "https://example.com/health",
                    "headers": {"Bad Name": "ok"},
                },
            }
        )


def test_target_config_persists_valid_http_headers() -> None:
    target = normalize_target_payload(
        {
            "label": "API",
            "host": "example.com",
            "scope": "external",
            "type": "api",
            "protocol": "https",
            "config": {
                "url": "https://example.com/health",
                "headers": {"X-Api-Key": "secret"},
            },
        }
    )
    assert target.config["headers"] == {"X-Api-Key": "secret"}
