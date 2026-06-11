"""macOS-specific helpers."""

from __future__ import annotations

import os
import platform
import subprocess

# Process `comm` fragments mapped to the name shown in Location Services.
_TERMINAL_CLIENTS: tuple[tuple[str, str], ...] = (
    ("cursor", "Cursor"),
    ("terminal", "Terminal"),
    ("iterm2", "iTerm"),
    ("iterm", "iTerm"),
    ("warp", "Warp"),
    ("kitty", "kitty"),
    ("alacritty", "Alacritty"),
    ("visual studio code", "Visual Studio Code"),
    ("code helper", "Visual Studio Code"),
    ("/code.app/", "Visual Studio Code"),
)


def _ps_field(pid: int, field: str) -> str:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", f"{field}="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _match_location_client(command: str, args: str) -> str | None:
    haystack = f"{command} {args}".lower()
    command_lower = command.lower()

    for needle, label in _TERMINAL_CLIENTS:
        if needle in haystack:
            return label

    if "netbox.app" in haystack or command_lower.endswith("netbox"):
        return "Netbox"

    if "python" in command_lower:
        return "Python"

    return None


def detect_location_client() -> str | None:
    """Best-effort name of the app to enable in Location Services."""

    if platform.system().lower() != "darwin":
        return None

    pid = os.getpid()
    seen: set[int] = set()
    matches: list[str] = []

    for _ in range(24):
        if pid in seen or pid <= 1:
            break
        seen.add(pid)

        command = _ps_field(pid, "comm")
        args = _ps_field(pid, "args")
        label = _match_location_client(command, args)
        if label and (not matches or matches[-1] != label):
            matches.append(label)

        ppid_text = _ps_field(pid, "ppid")
        if not ppid_text.isdigit():
            break
        pid = int(ppid_text)

    for label in matches:
        if label != "Python":
            return label
    return matches[0] if matches else None
