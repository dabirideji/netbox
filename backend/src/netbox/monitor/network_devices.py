"""Network device summaries and speed snapshots for live checks."""

from __future__ import annotations

from typing import Any

from netbox.core.models import NetworkIdentity
from netbox.probes.network import list_network_interfaces

PROPER_NETWORK_SERVICES = frozenset({"Wi-Fi", "Ethernet"})


def is_proper_network_device(option: dict[str, Any]) -> bool:
    """Return True for Wi-Fi or Ethernet interfaces shown in live checks."""

    service = option.get("service")
    if service not in PROPER_NETWORK_SERVICES:
        return False
    return not bool(option.get("hidden"))


def network_speed_snapshot(test: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert a stored speed test into the compact live-check shape."""

    if not test or test.get("status") != "completed":
        return None
    if test.get("downloadMbps") is None and test.get("uploadMbps") is None:
        return None
    return {
        "downloadMbps": test.get("downloadMbps"),
        "uploadMbps": test.get("uploadMbps"),
        "testedAt": test["testedAt"],
    }


def attach_network_identity(payload: dict[str, Any], network: NetworkIdentity) -> dict[str, Any]:
    """Attach the active network identity to a speed-test payload before persistence."""

    return {
        **payload,
        "networkName": network.name,
        "networkSsid": network.ssid,
        "networkInterface": network.interface,
        "networkService": network.service,
    }


def build_network_device_summaries(store: Any, network: NetworkIdentity) -> list[dict[str, Any]]:
    """Build live-check rows for each Wi-Fi or Ethernet interface."""

    devices: list[dict[str, Any]] = []
    for option in list_network_interfaces():
        if not is_proper_network_device(option):
            continue

        interface = option["interface"]
        test = store.latest_completed_speed_test_for_network(interface, option.get("ssid"))
        devices.append(
            {
                "id": f"network:{interface}",
                "interface": interface,
                "service": option.get("service"),
                "ssid": option.get("ssid"),
                "label": option.get("label") or interface,
                "active": bool(option.get("active")),
                "hidden": bool(option.get("hidden")),
                "networkSpeed": network_speed_snapshot(test),
            }
        )

    return devices


def enrich_summary_with_network_speed(
    summary: dict[str, Any],
    store: Any,
    network: NetworkIdentity,
) -> dict[str, Any]:
    """Attach network-device rows and speed snapshots to a status summary."""

    devices = build_network_device_summaries(store, network)
    active_speed = next((device["networkSpeed"] for device in devices if device["active"]), None)
    if active_speed is None:
        active_test = store.latest_completed_speed_test_for_network(network.interface, network.ssid)
        active_speed = network_speed_snapshot(active_test)

    targets = []
    for target in summary["targets"]:
        enriched = dict(target)
        if target.get("scope") == "gateway":
            enriched["networkSpeed"] = active_speed
        else:
            enriched["networkSpeed"] = None
        targets.append(enriched)

    return {**summary, "targets": targets, "networkDevices": devices}
