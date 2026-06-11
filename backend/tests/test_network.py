from netbox.models import NetworkIdentity
from netbox.network import (
    build_targets,
    clean_network_name,
    detect_network_identity,
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


def test_detect_network_identity_prefers_override() -> None:
    network = detect_network_identity("Office WiFi")

    assert network.name == "Office WiFi"
    assert network.ssid == "Office WiFi"


def test_wifi_ssid_likely_hidden_on_macos_wifi_without_ssid() -> None:
    network = NetworkIdentity(name="Wi-Fi (en0)", ssid=None, interface="en0", service="Wi-Fi")

    assert wifi_ssid_likely_hidden(network) is True


def test_wifi_ssid_likely_hidden_false_when_ssid_present() -> None:
    network = NetworkIdentity(name="Office WiFi", ssid="Office WiFi", interface="en0", service="Wi-Fi")

    assert wifi_ssid_likely_hidden(network) is False
