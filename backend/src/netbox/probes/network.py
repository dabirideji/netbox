"""Local gateway, interface, and Wi-Fi identity detection helpers."""

from __future__ import annotations

import platform
import re
import subprocess
from typing import Any

from netbox.core.models import NetworkIdentity, Target
from netbox.util.validation import parse_target_arg


def build_targets(
    custom_targets: list[str],
    gateway: str | None,
    default_external_targets: list[str] | None = None,
) -> list[Target]:
    """Build monitor targets from CLI overrides or sensible defaults."""

    if custom_targets:
        return [parse_target_arg(value, index) for index, value in enumerate(custom_targets)]

    targets: list[Target] = []
    if gateway:
        targets.append(Target("gateway", gateway, "Local Gateway", "gateway"))

    external_targets = default_external_targets if default_external_targets is not None else [
        "1.1.1.1:Cloudflare DNS:external",
        "8.8.8.8:Google DNS:external",
    ]
    targets.extend(parse_target_arg(value, index + len(targets)) for index, value in enumerate(external_targets))
    return targets


def detect_default_gateway() -> str | None:
    """Detect the default gateway for the active network route."""

    system = platform.system().lower()
    commands = (
        [["route", "-n", "get", "default"], ["netstat", "-rn"]]
        if system == "darwin"
        else [["ip", "route", "show", "default"], ["netstat", "-rn"]]
    )

    if system == "windows":
        commands = [["route", "print", "0.0.0.0"]]

    for command in commands:
        output = run_text(command)
        if not output:
            continue
        gateway = parse_gateway(output, system)
        if gateway:
            return gateway

    return None


def parse_gateway(output: str, system: str) -> str | None:
    """Extract a gateway IPv4 address from platform-specific route output."""

    if system == "darwin":
        return match_first(output, [r"gateway:\s*([0-9.]+)", r"^default\s+([0-9.]+)"])
    if system == "linux":
        return match_first(output, [r"default via\s+([0-9.]+)", r"^0\.0\.0\.0\s+([0-9.]+)"])
    if system == "windows":
        return match_first(output, [r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+([0-9.]+)"])
    return None


def network_identity_should_sync(current: NetworkIdentity, detected: NetworkIdentity) -> bool:
    """Return whether auto-detected network identity should replace the current one."""

    if current.interface != detected.interface:
        return True
    if detected.ssid and detected.ssid != current.ssid:
        return True
    if detected.ssid and not current.ssid:
        return True
    return False


def detect_network_identity(override_name: str = "") -> NetworkIdentity:
    """Return the active network identity, preferring an explicit Wi-Fi name."""

    system = platform.system().lower()
    interface = detect_default_interface(system)
    if interface:
        return detect_network_identity_for_interface(interface, override_name)
    return NetworkIdentity(name="Unknown network", ssid=None, interface=None, service=None)


def detect_network_identity_for_interface(interface: str, override_name: str = "") -> NetworkIdentity:
    """Return network identity for one interface, preferring an explicit Wi-Fi name."""

    system = platform.system().lower()
    service = detect_interface_service(interface) if system == "darwin" else _linux_interface_service(interface)
    ssid = clean_network_name(override_name) or detect_ssid(system, interface)
    name = ssid or format_interface_name(service, interface)
    return NetworkIdentity(name=name, ssid=ssid, interface=interface, service=service)


def list_network_interfaces() -> list[dict[str, Any]]:
    """List local network interfaces with best-effort SSID detection."""

    system = platform.system().lower()
    active = detect_default_interface(system)
    if system == "darwin":
        return _list_darwin_interfaces(active)
    if system == "linux":
        return _list_linux_interfaces(active)
    return []


def _list_darwin_interfaces(active: str | None) -> list[dict[str, Any]]:
    output = run_text(["networksetup", "-listallhardwareports"])
    if not output:
        return []

    options: list[dict[str, Any]] = []
    current_service: str | None = None

    for line in output.splitlines():
        if line.startswith("Hardware Port:"):
            current_service = line.split(":", 1)[1].strip()
            continue
        if not line.startswith("Device:"):
            continue

        interface = line.split(":", 1)[1].strip()
        if not interface:
            continue

        identity = detect_network_identity_for_interface(interface)
        options.append(_interface_option(identity, active))

    return options


def _list_linux_interfaces(active: str | None) -> list[dict[str, Any]]:
    output = run_text(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"])
    if not output:
        return []

    options: list[dict[str, Any]] = []
    for line in output.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue

        interface = parts[0].strip()
        device_type = parts[1].strip()
        state = parts[2].strip()
        if not interface or device_type == "loopback" or state in {"unmanaged", "unavailable"}:
            continue

        identity = detect_network_identity_for_interface(interface)
        service = _linux_interface_service(interface) or device_type
        options.append(
            _interface_option(
                NetworkIdentity(
                    name=identity.name,
                    ssid=identity.ssid,
                    interface=interface,
                    service=service,
                ),
                active,
            )
        )

    return options


def _linux_interface_service(interface: str) -> str | None:
    output = run_text(["nmcli", "-t", "-f", "TYPE", "device", "show", interface])
    if not output:
        return None

    device_type = output.splitlines()[0].strip()
    if device_type == "wifi":
        return "Wi-Fi"
    if device_type == "ethernet":
        return "Ethernet"
    return device_type or None


def _interface_option(identity: NetworkIdentity, active: str | None) -> dict[str, Any]:
    return {
        "service": identity.service,
        "interface": identity.interface,
        "ssid": identity.ssid,
        "active": identity.interface == active,
        "label": identity.name,
        "hidden": wifi_ssid_likely_hidden(identity),
    }


def detect_default_interface(system: str) -> str | None:
    """Detect the default route interface on Unix-like platforms."""

    commands = (
        [["route", "-n", "get", "default"], ["netstat", "-rn"]]
        if system == "darwin"
        else [["ip", "route", "show", "default"], ["netstat", "-rn"]]
    )

    if system == "windows":
        return None

    for command in commands:
        output = run_text(command)
        if not output:
            continue
        interface = match_first(
            output,
            [
                r"interface:\s*([^\s]+)",
                r"default via [0-9.]+ dev ([^\s]+)",
                r"^default\s+[0-9.]+\s+.*\s+([a-zA-Z0-9_.-]+)$",
            ],
        )
        if interface:
            return interface

    return None


def detect_interface_service(interface: str | None) -> str | None:
    """Map a macOS hardware interface such as `en0` to its service name."""

    if not interface or platform.system().lower() != "darwin":
        return None

    output = run_text(["networksetup", "-listallhardwareports"])
    if not output:
        return None

    current_port = None
    for line in output.splitlines():
        if line.startswith("Hardware Port:"):
            current_port = line.split(":", 1)[1].strip()
        elif line.startswith("Device:") and line.split(":", 1)[1].strip() == interface:
            return current_port

    return None


def detect_ssid(system: str, interface: str | None) -> str | None:
    """Best-effort Wi-Fi SSID detection with macOS privacy redaction handling."""

    if system == "darwin" and interface:
        networksetup_output = run_text(["networksetup", "-getairportnetwork", interface])
        ssid = clean_network_name(match_first(networksetup_output or "", [r"Current Wi-Fi Network:\s*(.+)$"]))
        if ssid:
            return ssid

        ipconfig_output = run_text(["ipconfig", "getsummary", interface])
        return clean_network_name(
            match_first(ipconfig_output or "", [r"^\s*SSID\s*:\s*(.+)$", r"^\s*NetworkID\s*:\s*(.+)$"])
        )

    if system == "linux":
        output = run_text(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
        for line in (output or "").splitlines():
            if line.startswith("yes:"):
                return clean_network_name(line.split(":", 1)[1])

    if system == "windows":
        output = run_text(["netsh", "wlan", "show", "interfaces"])
        return clean_network_name(match_first(output or "", [r"^\s*SSID\s*:\s*(.+)$"]))

    return None


def clean_network_name(value: str | None) -> str | None:
    """Normalize SSID strings and drop known redacted placeholder values."""

    if not value:
        return None

    name = value.strip().strip('"')
    hidden_values = {
        "",
        "<redacted>",
        "redacted",
        "(null)",
        "none",
        "not associated",
        "you are not associated with an airport network.",
    }
    if name.lower() in hidden_values or "not associated" in name.lower():
        return None
    return name


def wifi_ssid_likely_hidden(network: NetworkIdentity) -> bool:
    """Return True when macOS privacy likely hides the active Wi-Fi SSID."""

    if platform.system().lower() != "darwin":
        return False
    if network.ssid:
        return False
    if network.service == "Wi-Fi":
        return True
    return bool(network.interface and network.interface.startswith("en"))


def format_interface_name(service: str | None, interface: str | None) -> str:
    """Format a fallback network label when the SSID is unavailable."""

    if service and interface:
        return f"{service} ({interface})"
    if service:
        return service
    if interface:
        return interface
    return "Unknown network"


def match_first(value: str, patterns: list[str]) -> str | None:
    """Return the first regex capture found in multiline command output."""

    for pattern in patterns:
        found = re.search(pattern, value, re.MULTILINE)
        if found:
            return found.group(1).strip()
    return None


def run_text(command: list[str], timeout: int = 2) -> str | None:
    """Run a short system command and return stdout text on success."""

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return completed.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
