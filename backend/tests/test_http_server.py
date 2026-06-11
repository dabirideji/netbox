import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from netbox.core.models import MonitorConfig, NetworkIdentity, Target
from netbox.server import StatusHandler, StatusServer
from netbox.monitor.state import MonitorState
from netbox.storage import StatusStore


def config() -> MonitorConfig:
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
        db_path=":memory:",
    )


def test_status_server_serves_api_and_security_headers(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'></div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=3) as response:
            payload = json.load(response)
            csp = response.headers["Content-Security-Policy"]

        assert payload["network"]["ssid"] == "Test"
        assert "default-src 'self'" in csp
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()


def test_status_server_serves_openapi_and_swagger_docs(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'></div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/openapi.yaml", timeout=3) as response:
            body = response.read().decode()
            content_type = response.headers["Content-Type"]

        assert "openapi: 3.0.3" in body
        assert "Netbox Monitor API" in body
        assert "yaml" in content_type

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/docs", timeout=3) as response:
            html = response.read().decode()
            docs_csp = response.headers["Content-Security-Policy"]

        assert "swagger-ui" in html
        assert "/api/openapi.yaml" in html
        assert "script-src 'self' 'unsafe-inline'" in docs_csp

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/docs/swagger-ui/swagger-ui.css",
            timeout=3,
        ) as response:
            css = response.read().decode()

        assert ".swagger-ui" in css
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()


def test_status_server_serves_spa_fallback(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/dashboard", timeout=3) as response:
            body = response.read().decode()

        assert "id='app'" in body
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()


def test_status_server_serves_history(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    monitor_config = config()
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(monitor_config, [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    state.append_sample(
        {
            "checkedAt": 1_000,
            "results": [
                {
                    "id": target.id,
                    "host": target.host,
                    "label": target.label,
                    "scope": target.scope,
                    "ok": False,
                    "latencyMs": None,
                    "checkedAt": 1_000,
                    "durationMs": 10,
                    "error": "timeout",
                }
            ],
        }
    )
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/history?points=1", timeout=3) as response:
            payload = json.load(response)

        assert payload["points"] == [{"at": 1000, "severity": 2, "avgLatencyMs": None, "failurePct": 100.0}]
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_serves_filtered_events(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    monitor_config = config()
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(monitor_config, [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    state.append_sample(
        {
            "checkedAt": 1_000,
            "results": [
                {
                    "id": target.id,
                    "host": target.host,
                    "label": target.label,
                    "scope": target.scope,
                    "ok": True,
                    "latencyMs": 5,
                    "checkedAt": 1_000,
                    "durationMs": 10,
                    "error": None,
                }
            ],
        }
    )
    state.append_sample(
        {
            "checkedAt": 2_000,
            "results": [
                {
                    "id": target.id,
                    "host": target.host,
                    "label": target.label,
                    "scope": target.scope,
                    "ok": False,
                    "latencyMs": None,
                    "checkedAt": 2_000,
                    "durationMs": 10,
                    "error": "timeout",
                }
            ],
        }
    )
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/events?from=1500&to=2500&limit=10&offset=0",
            timeout=3,
        ) as response:
            payload = json.load(response)

        assert payload["limit"] == 10
        assert payload["offset"] == 0
        assert payload["total"] == 1
        assert payload["events"][0]["targetLabel"] == "Loopback"
        assert payload["events"][0]["to"] == "degraded"
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_serves_target_history(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    state.append_sample(
        {
            "checkedAt": 1_000,
            "results": [
                {
                    "id": target.id,
                    "host": target.host,
                    "label": target.label,
                    "scope": target.scope,
                    "ok": True,
                    "latencyMs": 5,
                    "checkedAt": 1_000,
                    "durationMs": 10,
                    "error": None,
                }
            ],
        }
    )
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/targets/history?points=1", timeout=3) as response:
            payload = json.load(response)

        assert payload["targets"][0]["id"] == "gateway"
        assert payload["targets"][0]["points"][0]["status"] == "operational"
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_records_and_serves_speed_tests(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    monitor_config = config()
    state = MonitorState(monitor_config, [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/speed-tests",
            data=json.dumps(
                {
                    "testedAt": 4_000,
                    "provider": "mlab-ndt7",
                    "status": "completed",
                    "downloadMbps": 100.1,
                    "uploadMbps": 25.5,
                    "latencyMs": 19.2,
                    "durationMs": 21_000,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            created = json.load(response)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/speed-tests?limit=5", timeout=3) as response:
            payload = json.load(response)

        assert created["test"]["downloadMbps"] == 100.1
        assert payload["total"] == 1
        assert payload["policy"]["provider"] == "mlab-ndt7"
        assert payload["tests"][0]["uploadMbps"] == 25.5
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_rejects_invalid_speed_test_payload(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/speed-tests",
            data=json.dumps({"testedAt": 4_000, "status": "impossible"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("Expected invalid speed payload to return HTTP 400")
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_rejects_invalid_date_range(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/history?from=2500&to=1500", timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("Expected invalid range to return HTTP 400")
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()


def test_status_server_serves_and_updates_preferences(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/preferences", timeout=3) as response:
            payload = json.load(response)

        assert payload["data"] == {}

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/preferences",
            data=json.dumps(
                {"dashboard_sections_collapsed": {"timeline": True, "speedTest": False}},
            ).encode(),
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            updated = json.load(response)

        assert updated["data"]["dashboard_sections_collapsed"]["timeline"] is True
        assert updated["data"]["dashboard_sections_collapsed"]["speedTest"] is False
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_serves_and_clears_storage(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
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
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/storage", timeout=3) as response:
            stats = json.load(response)

        assert stats["usage"]["incidents"] == 1
        assert stats["limits"]["maxIncidents"] == 1_000_000

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/storage/clear",
            data=json.dumps({"scope": "incidents"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            cleared = json.load(response)

        assert cleared["deleted"]["incidents"] == 1
        assert cleared["stats"]["usage"]["incidents"] == 0
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_cruds_targets(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    seed = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([seed])
    state = MonitorState(config(), [seed], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/targets", timeout=3) as response:
            initial = json.load(response)

        create_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/targets",
            data=json.dumps(
                {
                    "label": "Example",
                    "protocol": "tcp",
                    "type": "port",
                    "scope": "external",
                    "config": {"host": "example.com", "port": 443},
                }
            ).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(create_request, timeout=3) as response:
            created = json.load(response)

        patch_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/targets/{created['target']['id']}",
            data=json.dumps({"enabled": False}).encode(),
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(patch_request, timeout=3) as response:
            updated = json.load(response)

        delete_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/targets/{created['target']['id']}",
            method="DELETE",
        )
        with urllib.request.urlopen(delete_request, timeout=3) as response:
            deleted = json.load(response)

        assert initial["targets"][0]["id"] == "gateway"
        assert created["target"]["protocol"] == "tcp"
        assert updated["target"]["enabled"] is False
        assert deleted["deleted"] is True
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_reorders_targets(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([Target("gateway", "127.0.0.1", "Loopback", "gateway")])
    created = store.create_target(
        {
            "label": "Example",
            "protocol": "tcp",
            "type": "port",
            "scope": "external",
            "config": {"host": "example.com", "port": 443},
        }
    )
    state = MonitorState(config(), store.list_targets(), NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        reorder_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/targets/order",
            data=json.dumps({"order": [created.id, "gateway"]}).encode(),
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(reorder_request, timeout=3) as response:
            payload = json.load(response)

        assert [target["id"] for target in payload["targets"]] == [created.id, "gateway"]
        assert [target["sortOrder"] for target in payload["targets"]] == [0, 1]
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_sets_target_favorite(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    store = StatusStore(tmp_path / "status.sqlite3")
    store.seed_targets([Target("gateway", "127.0.0.1", "Loopback", "gateway")])
    state = MonitorState(config(), store.list_targets(), NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        favorite_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/targets/gateway/favorite",
            data=json.dumps({"favorite": True}).encode(),
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(favorite_request, timeout=3) as response:
            payload = json.load(response)

        assert payload["target"]["isFavorite"] is True

        status_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(status_request, timeout=3) as response:
            status_payload = json.load(response)

        gateway = next(target for target in status_payload["targets"] if target["id"] == "gateway")
        assert gateway["isFavorite"] is True
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()


def test_status_server_rejects_invalid_target_payload(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id='app'>ok</div>")
    store = StatusStore(tmp_path / "status.sqlite3")
    state = MonitorState(config(), [], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0, store)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/targets",
            data=json.dumps({"label": "Bad", "protocol": "tcp", "config": {"port": 70000}}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("Expected invalid target payload to return HTTP 400")
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()
