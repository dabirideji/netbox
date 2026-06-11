from pathlib import Path

from netbox.models import MonitorConfig, Target
from netbox.storage import StatusStore


def config(db_path: Path) -> MonitorConfig:
    return MonitorConfig(
        duration_ms=None,
        interval_ms=1_000,
        timeout_ms=900,
        port=4177,
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


def sample(checked_at: int, ok: bool, latency_ms: float | None) -> dict[str, object]:
    return {
        "checkedAt": checked_at,
        "results": [
            {
                "id": "gateway",
                "host": "127.0.0.1",
                "label": "Loopback",
                "scope": "gateway",
                "ok": ok,
                "latencyMs": latency_ms,
                "checkedAt": checked_at,
                "durationMs": 10,
                "error": None if ok else "timeout",
            }
        ],
    }


def https_sample(checked_at: int, latency_ms: float) -> dict[str, object]:
    return {
        "checkedAt": checked_at,
        "results": [
            {
                "id": "jobbox-website",
                "host": "getjobbox.com",
                "label": "Jobbox",
                "scope": "external",
                "type": "website",
                "protocol": "https",
                "ok": True,
                "latencyMs": latency_ms,
                "checkedAt": checked_at,
                "durationMs": latency_ms,
                "error": None,
            }
        ],
    }


def test_status_store_classifies_https_latency_as_operational(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    monitor_config = config(db_path)

    try:
        store.record_sample(https_sample(1_000, 2_500), monitor_config)
        row = store.connection.execute(
            "SELECT status FROM check_results WHERE target_id = ?",
            ("jobbox-website",),
        ).fetchone()
    finally:
        store.close()

    assert row is not None
    assert row[0] == "operational"


def test_status_store_creates_database_when_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "netbox.sqlite3"
    assert not db_path.exists()
    assert not db_path.parent.exists()

    store = StatusStore(db_path)

    try:
        assert db_path.is_file()
        tables = {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        }
        assert "ping_results" in tables
        assert "monitor_targets" in tables
        assert "check_results" in tables
        assert "incidents" in tables
        assert "status_events" in tables
        assert "speed_tests" in tables
        assert "ui_preferences" in tables
    finally:
        store.close()


def test_status_store_persists_history_points(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    monitor_config = config(db_path)

    try:
        store.record_sample(sample(1_000, True, 10), monitor_config)
        store.record_sample(sample(2_000, True, 150), monitor_config)
        store.record_sample(sample(3_000, False, None), monitor_config)

        history = store.history_overview(points=2)
    finally:
        store.close()

    assert history["points"] == [
        {"at": 2000, "severity": 1, "avgLatencyMs": 150.0, "failurePct": 0.0},
        {"at": 3000, "severity": 2, "avgLatencyMs": None, "failurePct": 100.0},
    ]


def test_status_store_filters_history_by_date_range(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    monitor_config = config(db_path)

    try:
        store.record_sample(sample(1_000, True, 10), monitor_config)
        store.record_sample(sample(2_000, True, 150), monitor_config)
        store.record_sample(sample(3_000, False, None), monitor_config)

        history = store.history_overview(points=10, from_ms=1_500, to_ms=2_500)
    finally:
        store.close()

    assert history["from"] == 1500
    assert history["to"] == 2500
    assert history["points"] == [{"at": 2000, "severity": 1, "avgLatencyMs": 150.0, "failurePct": 0.0}]


def test_status_store_returns_per_target_history(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    monitor_config = config(db_path)

    try:
        store.record_sample(sample(1_000, True, 10), monitor_config)
        store.record_sample(sample(2_000, False, None), monitor_config)

        history = store.target_history(points=10)
    finally:
        store.close()

    assert history["targets"] == [
        {
            "id": "gateway",
            "host": "127.0.0.1",
            "label": "Loopback",
            "scope": "gateway",
            "type": "host",
            "protocol": "icmp",
            "points": [
                {
                    "at": 1000,
                    "severity": 0,
                    "status": "operational",
                    "ok": True,
                    "latencyMs": 10.0,
                    "error": None,
                },
                {
                    "at": 2000,
                    "severity": 2,
                    "status": "down",
                    "ok": False,
                    "latencyMs": None,
                    "error": "timeout",
                },
            ],
        }
    ]


def test_status_store_seeds_and_cruds_targets(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)

    try:
        store.seed_targets([Target("gateway", "127.0.0.1", "Loopback", "gateway")])
        created = store.create_target(
            {
                "label": "Example API",
                "protocol": "http",
                "type": "api",
                "scope": "external",
                "config": {"url": "https://example.com/health", "expectedStatus": 204},
            }
        )
        updated = store.update_target(created.id, {"enabled": False, "group": "Production"})
        deleted = store.delete_target(created.id)
        targets = store.list_targets()
    finally:
        store.close()

    assert targets[0].id == "gateway"
    assert created.protocol == "http"
    assert updated.enabled is False
    assert updated.group == "Production"
    assert deleted is True


def test_status_store_returns_target_results(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    monitor_config = config(db_path)

    try:
        store.record_sample(sample(1_000, True, 10), monitor_config)
        store.record_sample(sample(2_000, False, None), monitor_config)
        results = store.target_results("gateway", limit=10)
    finally:
        store.close()

    assert results["total"] == 2
    assert results["results"][0]["checkedAt"] == 2_000
    assert results["results"][0]["status"] == "down"


def test_status_store_opens_and_resolves_incidents(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    down_event = {
        "at": 1_000,
        "targetId": "gateway",
        "targetLabel": "Loopback",
        "from": "operational",
        "to": "degraded",
        "message": "Loopback changed from operational to degraded",
    }
    up_event = {
        **down_event,
        "at": 2_000,
        "from": "degraded",
        "to": "operational",
        "message": "Loopback changed from degraded to operational",
    }

    try:
        store.record_incident_events([down_event])
        open_incidents = store.recent_incidents()
        store.record_incident_events([up_event])
        resolved_incidents = store.recent_incidents()
    finally:
        store.close()

    assert open_incidents["incidents"][0]["status"] == "open"
    assert resolved_incidents["incidents"][0]["status"] == "resolved"
    assert resolved_incidents["incidents"][0]["resolvedAt"] == 2_000


def test_status_store_persists_status_events(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    event = {
        "at": 2_000,
        "targetId": "gateway",
        "targetLabel": "Loopback",
        "from": "operational",
        "to": "degraded",
        "message": "Loopback changed from operational to degraded",
    }

    try:
        store.record_events([event, event])
        result = store.recent_events()
    finally:
        store.close()

    assert result["limit"] == 50
    assert result["offset"] == 0
    assert result["total"] == 1
    assert result["events"] == [event]


def test_status_store_filters_events_by_date_range(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    early_event = {
        "at": 1_000,
        "targetId": "gateway",
        "targetLabel": "Loopback",
        "from": "operational",
        "to": "degraded",
        "message": "Loopback changed from operational to degraded",
    }
    late_event = {
        **early_event,
        "at": 3_000,
        "from": "degraded",
        "to": "down",
        "message": "Loopback changed from degraded to down",
    }

    try:
        store.record_events([early_event, late_event])
        result = store.recent_events(from_ms=2_000, to_ms=4_000)
    finally:
        store.close()

    assert result["total"] == 1
    assert result["events"] == [late_event]


def test_status_store_paginates_events_newest_first(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    events = [
        {
            "at": timestamp,
            "targetId": "gateway",
            "targetLabel": "Loopback",
            "from": "operational",
            "to": "degraded",
            "message": f"event {timestamp}",
        }
        for timestamp in [1_000, 2_000, 3_000]
    ]

    try:
        store.record_events(events)
        page = store.recent_events(limit=1, offset=1)
    finally:
        store.close()

    assert page["total"] == 3
    assert page["events"][0]["at"] == 2_000


def test_status_store_persists_speed_tests(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)

    try:
        saved = store.record_speed_test(
            {
                "testedAt": 4_000,
                "provider": "mlab-ndt7",
                "status": "completed",
                "downloadMbps": 120.5,
                "uploadMbps": 42.2,
                "latencyMs": 18.1,
                "jitterMs": 2.4,
                "packetLossPct": 0.0,
                "retransmissionPct": 0.1,
                "durationMs": 21_000,
                "serverName": "mlab-test",
                "serverLocation": "Lagos",
                "serverHost": "ndt.example.net",
                "error": None,
            }
        )
        result = store.recent_speed_tests(limit=10)
    finally:
        store.close()

    assert saved["downloadMbps"] == 120.5
    assert result["total"] == 1
    assert result["stats"]["avgDownloadMbps"] == 120.5
    assert result["tests"][0]["serverLocation"] == "Lagos"


def test_status_store_filters_speed_tests_by_date_range(tmp_path: Path) -> None:
    db_path = tmp_path / "status.sqlite3"
    store = StatusStore(db_path)
    speed_test = {
        "provider": "mlab-ndt7",
        "status": "failed",
        "downloadMbps": None,
        "uploadMbps": None,
        "latencyMs": None,
        "jitterMs": None,
        "packetLossPct": None,
        "retransmissionPct": None,
        "durationMs": 100,
        "serverName": None,
        "serverLocation": None,
        "serverHost": None,
        "error": "network unavailable",
    }

    try:
        store.record_speed_test({**speed_test, "testedAt": 1_000})
        store.record_speed_test({**speed_test, "testedAt": 3_000})
        result = store.recent_speed_tests(limit=10, from_ms=2_000, to_ms=4_000)
    finally:
        store.close()

    assert result["total"] == 1
    assert result["tests"][0]["testedAt"] == 3_000
    assert result["tests"][0]["status"] == "failed"


def test_status_store_persists_ui_preferences(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")

    try:
        merged = store.update_preferences({"dashboard_sections_collapsed": {"timeline": True}})
        assert merged["dashboard_sections_collapsed"]["timeline"] is True

        current = store.get_preferences()
        assert current["dashboard_sections_collapsed"]["timeline"] is True

        merged_again = store.update_preferences({"dashboard_home_mode": "compact"})
        assert merged_again["dashboard_sections_collapsed"]["timeline"] is True
        assert merged_again["dashboard_home_mode"] == "compact"

        merged_sections = store.update_preferences(
            {"dashboard_sections_collapsed": {"incidentLog": True}},
        )
        assert merged_sections["dashboard_sections_collapsed"]["timeline"] is True
        assert merged_sections["dashboard_sections_collapsed"]["incidentLog"] is True
    finally:
        store.close()


def test_status_store_enforces_incident_limit(tmp_path: Path) -> None:
    store = StatusStore(
        tmp_path / "status.sqlite3",
        {
            "autoPrune": True,
            "limits": {
                "maxDatabaseBytes": 52_428_800,
                "maxIncidents": 3,
                "maxPingSamples": 100,
                "maxSpeedTests": 10,
            },
        },
    )

    try:
        for index in range(5):
            store.record_events(
                [
                    {
                        "at": index * 1_000,
                        "targetId": "gateway",
                        "targetLabel": "Gateway",
                        "from": "operational",
                        "to": "degraded",
                        "message": f"event {index}",
                    }
                ]
            )

        stats = store.storage_stats()
        assert stats["usage"]["incidents"] == 3
        assert stats["percentUsed"]["incidents"] == 100.0
    finally:
        store.close()


def test_status_store_clear_storage_scope(tmp_path: Path) -> None:
    store = StatusStore(tmp_path / "status.sqlite3")

    try:
        store.record_events(
            [
                {
                    "at": 1_000,
                    "targetId": "gateway",
                    "targetLabel": "Gateway",
                    "from": "operational",
                    "to": "down",
                    "message": "offline",
                }
            ]
        )
        result = store.clear_storage("incidents")
        assert result["deleted"]["incidents"] == 1
        assert result["stats"]["usage"]["incidents"] == 0
    finally:
        store.close()
