"""Terminal dashboard rendering utilities."""

from __future__ import annotations

from typing import Any

from netbox.models import MonitorConfig
from netbox.timeutils import format_clock, format_duration


def render_dashboard(summary: dict[str, Any], config: MonitorConfig) -> None:
    """Render the compact terminal status dashboard for the latest summary."""

    elapsed = format_duration(summary["now"] - summary["startedAt"])
    remaining = (
        "until stopped"
        if summary["endsAt"] is None
        else format_duration(max(0, summary["endsAt"] - summary["now"]))
    )
    status = summary["overallStatus"]

    print("\033c", end="")
    print(f"{bold('Netbox')} {dim('Atlassian-ish, but for your router gremlins')}")
    print(
        f"{dim('Network')} {summary['network']['name']}  "
        f"{dim('URL')} http://localhost:{config.port}  "
        f"{dim('Elapsed')} {elapsed}  {dim('Remaining')} {remaining}"
    )
    print()
    print(f"{color_for(status)(symbol_for(status))} {color_for(status)(status.upper())} - {summary['diagnosis']}")
    print()
    print(
        f"{pad('Component', 20)} {pad('Status', 13)} {pad('Last', 10)} {pad('Loss', 8)} "
        f"{pad('Avg', 9)} {pad('Jitter', 9)} {pad('Host', 16)}"
    )
    print(dim("─" * 91))

    for target in summary["targets"]:
        target_status = target["currentStatus"]
        last = target["lastError"] or "fail" if target["lastLatencyMs"] is None else f"{target['lastLatencyMs']:.1f}ms"
        print(
            f"{pad(target['label'], 20)} "
            f"{color_for(target_status)(pad(symbol_for(target_status) + ' ' + target_status, 13))} "
            f"{pad(last, 10)} "
            f"{pad(format_pct(target['packetLossPct']), 8)} "
            f"{pad(format_ms(target['avgLatencyMs']), 9)} "
            f"{pad(format_ms(target['jitterMs']), 9)} "
            f"{pad(target['host'], 16)}"
        )

    print()
    print(bold("Recent events"))
    recent_events = summary["events"][-6:]
    if not recent_events:
        print(dim("No incidents yet. The network goblin is behaving."))
    else:
        for event in recent_events:
            print(f"{dim(format_clock(event['at']))} {event['message']}")
    print()
    print(dim("Press Ctrl+C to stop. Default run length is indefinite."))


def print_startup(config: MonitorConfig, targets: list[Any]) -> None:
    """Print startup metadata before the first monitor sample arrives."""

    run_window = "indefinitely" if config.duration_ms is None else f"for {format_duration(config.duration_ms)}"
    print(f"Starting local network monitor {run_window}.")
    print(f"Status page: http://localhost:{config.port}")
    print(f"Targets: {', '.join(f'{target.label} ({target.host})' for target in targets)}")


def format_pct(value: float) -> str:
    return f"{value:.1f}%"


def format_ms(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}ms"


def color_for(status: str) -> Any:
    return {
        "operational": green,
        "degraded": yellow,
        "down": red,
        "unknown": dim,
    }.get(status, dim)


def symbol_for(status: str) -> str:
    return {
        "operational": "●",
        "degraded": "▲",
        "down": "■",
        "unknown": "○",
    }.get(status, "○")


def pad(value: Any, width: int) -> str:
    text = str(value)
    return text[: width - 1] + "…" if len(text) >= width else text.ljust(width)


def bold(value: str) -> str:
    return f"\033[1m{value}\033[0m"


def dim(value: str) -> str:
    return f"\033[2m{value}\033[0m"


def green(value: str) -> str:
    return f"\033[32m{value}\033[0m"


def yellow(value: str) -> str:
    return f"\033[33m{value}\033[0m"


def red(value: str) -> str:
    return f"\033[31m{value}\033[0m"
