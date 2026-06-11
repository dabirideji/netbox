from netbox.core.responses import (
    STATUS_SEVERITY,
    VALID_SPEED_STATUSES,
    api_error_body,
    api_error_code_for_message,
    monitor_status_code,
    monitor_status_severity,
    normalize_monitor_status,
    speed_test_status_code,
    storage_clear_scope_code,
    stream_event_code,
    terminal_symbol,
)


def test_monitor_status_registry_maps_severity_and_codes() -> None:
    assert STATUS_SEVERITY["operational"] == 0
    assert STATUS_SEVERITY["degraded"] == 1
    assert STATUS_SEVERITY["down"] == 2
    assert monitor_status_code("operational") == "MON-000"
    assert monitor_status_code("degraded") == "MON-110"
    assert monitor_status_code("down") == "MON-120"
    assert monitor_status_severity("down") == 2
    assert normalize_monitor_status("bogus") == "unknown"
    assert terminal_symbol("degraded") == "▲"


def test_speed_stream_and_storage_codes() -> None:
    assert frozenset({"completed", "failed"}) == VALID_SPEED_STATUSES
    assert speed_test_status_code("completed") == "SPD-000"
    assert stream_event_code("speedTest") == "SSE-004"
    assert storage_clear_scope_code("ping") == "STG-002"


def test_api_error_payload_and_code_resolution() -> None:
    assert api_error_body("API-4001", "from must be less than or equal to to") == {
        "code": "API-4001",
        "error": "from must be less than or equal to to",
    }
    assert api_error_code_for_message("from must be less than or equal to to") == "API-4001"
    assert api_error_code_for_message("target was not found") == "API-4040"
    assert api_error_code_for_message("protocol must be one of dns, http, https, icmp, tcp") == "API-4006"
