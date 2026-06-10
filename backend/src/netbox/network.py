"""Local gateway, interface, and Wi-Fi identity detection helpers."""

from __future__ import annotations

import platform
import re
import subprocess

from netbox.models import NetworkIdentity, Target
from netbox.validation import parse_target_arg


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

    external_targets = default_external_targets or [
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


def detect_network_identity(override_name: str = "") -> NetworkIdentity:
    """Return the active network identity, preferring an explicit Wi-Fi name."""

    system = platform.system().lower()
    interface = detect_default_interface(system)
    service = detect_interface_service(interface) if interface else None
    ssid = clean_network_name(override_name) or detect_ssid(system, interface)
    name = ssid or format_interface_name(service, interface)

    return NetworkIdentity(name=name, ssid=ssid, interface=interface, service=service)


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
