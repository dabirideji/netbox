"""Network device live-check enrichment tests."""

from netbox.monitor.network_devices import (
    build_network_device_summaries,
    enrich_summary_with_network_speed,
    is_proper_network_device,
    network_speed_snapshot,
)
from netbox.storage import StatusStore


def test_is_proper_network_device_filters_hidden_and_non_physical() -> None:
    assert is_proper_network_device({"service": "Wi-Fi", "hidden": False}) is True
    assert is_proper_network_device({"service": "Ethernet", "hidden": False}) is True
    assert is_proper_network_device({"service": "Wi-Fi", "hidden": True}) is False
    assert is_proper_network_device({"service": "Thunderbolt Bridge", "hidden": False}) is False


def test_network_speed_snapshot_requires_completed_results() -> None:
    assert network_speed_snapshot(None) is None
    assert network_speed_snapshot({"status": "failed", "testedAt": 1, "downloadMbps": 10, "uploadMbps": 5}) is None
    assert network_speed_snapshot({"status": "completed", "testedAt": 1, "downloadMbps": None, "uploadMbps": None}) is None
    assert network_speed_snapshot({"status": "completed", "testedAt": 1, "downloadMbps": 100.5, "uploadMbps": 25.0}) == {
        "downloadMbps": 100.5,
        "uploadMbps": 25.0,
        "testedAt": 1,
    }


def test_latest_completed_speed_test_for_network_prefers_interface(tmp_path) -> None:
    store = StatusStore(tmp_path / "netbox.db")
    try:
        store.record_speed_test(
            {
                "testedAt": 1_000,
                "provider": "mlab-ndt7",
                "status": "completed",
                "downloadMbps": 50.0,
                "uploadMbps": 10.0,
                "latencyMs": 12.0,
                "jitterMs": None,
                "packetLossPct": None,
                "retransmissionPct": None,
                "durationMs": 1000,
                "serverName": None,
                "serverLocation": None,
                "serverHost": None,
                "error": None,
                "networkInterface": "en0",
                "networkSsid": "Office",
            }
        )
        store.record_speed_test(
            {
                "testedAt": 2_000,
                "provider": "mlab-ndt7",
                "status": "completed",
                "downloadMbps": 80.0,
                "uploadMbps": 20.0,
                "latencyMs": 10.0,
                "jitterMs": None,
                "packetLossPct": None,
                "retransmissionPct": None,
                "durationMs": 1000,
                "serverName": None,
                "serverLocation": None,
                "serverHost": None,
                "error": None,
                "networkInterface": "en7",
                "networkSsid": "Guest",
            }
        )

        match = store.latest_completed_speed_test_for_network("en0", "Office")
        assert match is not None
        assert match["downloadMbps"] == 50.0
    finally:
        store.close()


def test_enrich_summary_with_network_speed_attaches_gateway_speed(tmp_path, monkeypatch) -> None:
    store = StatusStore(tmp_path / "netbox.db")
    monkeypatch.setattr(
        "netbox.monitor.network_devices.list_network_interfaces",
        lambda: [
            {
                "service": "Wi-Fi",
                "interface": "en0",
                "ssid": "Office",
                "active": True,
                "label": "Office WiFi",
                "hidden": False,
            }
        ],
    )
    try:
        store.record_speed_test(
            {
                "testedAt": 3_000,
                "provider": "mlab-ndt7",
                "status": "completed",
                "downloadMbps": 120.0,
                "uploadMbps": 42.0,
                "latencyMs": 9.0,
                "jitterMs": None,
                "packetLossPct": None,
                "retransmissionPct": None,
                "durationMs": 1000,
                "serverName": None,
                "serverLocation": None,
                "serverHost": None,
                "error": None,
                "networkInterface": "en0",
                "networkSsid": "Office",
            }
        )

        from netbox.core.models import NetworkIdentity

        summary = {
            "targets": [
                {"id": "gateway", "scope": "gateway", "label": "Gateway"},
                {"id": "dns", "scope": "external", "label": "DNS"},
            ]
        }
        enriched = enrich_summary_with_network_speed(
            summary,
            store,
            NetworkIdentity(name="Office WiFi", ssid="Office", interface="en0", service="Wi-Fi"),
        )

        assert enriched["networkDevices"][0]["networkSpeed"]["downloadMbps"] == 120.0
        assert enriched["targets"][0]["networkSpeed"]["uploadMbps"] == 42.0
        assert enriched["targets"][1]["networkSpeed"] is None
    finally:
        store.close()


def test_build_network_device_summaries_lists_proper_interfaces(monkeypatch) -> None:
    monkeypatch.setattr(
        "netbox.monitor.network_devices.list_network_interfaces",
        lambda: [
            {
                "service": "Wi-Fi",
                "interface": "en0",
                "ssid": "Office",
                "active": True,
                "label": "Office WiFi",
                "hidden": False,
            },
            {
                "service": "Thunderbolt Bridge",
                "interface": "bridge0",
                "ssid": None,
                "active": False,
                "label": "Bridge",
                "hidden": False,
            },
        ],
    )

    class EmptyStore:
        def latest_completed_speed_test_for_network(self, interface: str | None, ssid: str | None) -> None:
            return None

    devices = build_network_device_summaries(EmptyStore(), None)  # type: ignore[arg-type]
    assert len(devices) == 1
    assert devices[0]["interface"] == "en0"
