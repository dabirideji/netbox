from netbox.core.models import NetworkIdentity
from netbox.probes.network import (
    build_targets,
    clean_network_name,
    detect_network_identity,
    detect_network_identity_for_interface,
    list_network_interfaces,
    network_identity_should_sync,
    parse_gateway,
    wifi_ssid_likely_hidden,
)


def test_clean_network_name_hides_redacted_values() -> None:
    assert clean_network_name("<redacted>") is None
    assert clean_network_name("You are not associated with an AirPort network.") is None
    assert clean_network_name("Office WiFi") == "Office WiFi"


def test_parse_gateway_for_darwin_route_output() -> None:
    output = """
       route to: default
    destination: default
        gateway: 192.168.18.1
      interface: en0
    """
    assert parse_gateway(output, "darwin") == "192.168.18.1"


def test_parse_gateway_for_linux_route_output() -> None:
    assert parse_gateway("default via 10.0.0.1 dev wlan0 proto dhcp", "linux") == "10.0.0.1"


def test_build_targets_uses_defaults_with_gateway() -> None:
    targets = build_targets([], "192.168.1.1")

    assert targets[0].scope == "gateway"
    assert {target.host for target in targets} == {"192.168.1.1", "1.1.1.1", "8.8.8.8"}


def test_build_targets_uses_custom_targets() -> None:
    targets = build_targets(["10.0.0.1:Router:gateway"], None)

    assert len(targets) == 1
    assert targets[0].label == "Router"


def test_build_targets_uses_configured_default_external_targets() -> None:
    targets = build_targets([], "192.168.1.1", ["9.9.9.9:Quad9 DNS:external"])

    assert [target.host for target in targets] == ["192.168.1.1", "9.9.9.9"]
    assert targets[1].label == "Quad9 DNS"


def test_network_identity_should_sync_on_new_ssid() -> None:
    current = NetworkIdentity(name="Home", ssid="Home", interface="en0", service="Wi-Fi")
    detected = NetworkIdentity(name="Office", ssid="Office", interface="en0", service="Wi-Fi")

    assert network_identity_should_sync(current, detected) is True


def test_network_identity_should_sync_keeps_manual_when_detection_fails() -> None:
    current = NetworkIdentity(name="Home", ssid="Home", interface="en0", service="Wi-Fi")
    detected = NetworkIdentity(name="Wi-Fi (en0)", ssid=None, interface="en0", service="Wi-Fi")

    assert network_identity_should_sync(current, detected) is False


def test_detect_network_identity_prefers_override() -> None:
    network = detect_network_identity("Office WiFi")

    assert network.name == "Office WiFi"
    assert network.ssid == "Office WiFi"


def test_list_network_interfaces_parses_darwin_hardware_ports(monkeypatch) -> None:
    listing = """
Hardware Port: Wi-Fi
Device: en0
Ethernet Address: aa:bb

Hardware Port: Ethernet
Device: en7
Ethernet Address: cc:dd
"""

    def fake_run_text(command: list[str], timeout: int = 2) -> str | None:
        if command[:2] == ["networksetup", "-listallhardwareports"]:
            return listing
        if command[:3] == ["networksetup", "-getairportnetwork", "en0"]:
            return "Current Wi-Fi Network: Office WiFi"
        if command[:3] == ["networksetup", "-getairportnetwork", "en7"]:
            return "You are not associated with an AirPort network."
        if command[:2] == ["route", "-n"]:
            return "interface: en0"
        return None

    monkeypatch.setattr("netbox.probes.network.platform.system", lambda: "Darwin")
    monkeypatch.setattr("netbox.probes.network.run_text", fake_run_text)

    options = list_network_interfaces()

    assert len(options) == 2
    assert options[0]["interface"] == "en0"
    assert options[0]["ssid"] == "Office WiFi"
    assert options[0]["active"] is True
    assert options[1]["interface"] == "en7"


def test_detect_network_identity_for_interface_uses_service_label(monkeypatch) -> None:
    monkeypatch.setattr("netbox.probes.network.platform.system", lambda: "Darwin")
    monkeypatch.setattr("netbox.probes.network.run_text", lambda command, timeout=2: None)

    network = detect_network_identity_for_interface("en7")

    assert network.interface == "en7"
    assert network.name == "en7"


def test_wifi_ssid_likely_hidden_on_macos_wifi_without_ssid() -> None:
    network = NetworkIdentity(name="Wi-Fi (en0)", ssid=None, interface="en0", service="Wi-Fi")

    assert wifi_ssid_likely_hidden(network) is True


def test_wifi_ssid_likely_hidden_false_when_ssid_present() -> None:
    network = NetworkIdentity(name="Office WiFi", ssid="Office WiFi", interface="en0", service="Wi-Fi")

    assert wifi_ssid_likely_hidden(network) is False
