"""CLI parsing and monitor process lifecycle."""

from __future__ import annotations

import argparse
import errno
import os
import signal
import sys
import threading
from pathlib import Path

from netbox.config import (
    env_bool,
    env_float,
    env_int,
    env_str,
    load_default_target_args,
    load_default_target_seeds,
    load_env_files,
    load_json_config,
    load_security_config,
    load_speed_config,
    load_storage_config,
    nested,
    resolve_project_path,
)
from netbox.core.models import MonitorConfig, Target
from netbox.probes.network import build_targets, detect_default_gateway, detect_network_identity
from netbox.util.paths import project_root
from netbox.monitor.scheduler import TargetScheduler
from netbox.server import StatusHandler, StatusServer
from netbox.monitor.state import MonitorState
from netbox.storage import StatusStore
from netbox.targets import gateway_host_sync_payload, repair_api_health_targets, target_from_seed
from netbox.monitor.terminal import print_startup, render_dashboard
from netbox.util.timeutils import format_duration, now_ms, parse_duration
from netbox.util.validation import validate_bind_host, validate_port

PROJECT_ROOT = project_root()
DEFAULT_STATIC_DIR = PROJECT_ROOT / "frontend" / "dist"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "netbox.sqlite3"


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and run the monitor process."""

    try:
        args = list(argv if argv is not None else sys.argv[1:])
        if args[:1] == ["seed"]:
            return seed_defaults(parse_args(args[1:]))
        config = parse_args(args)
        return run(config)
    except ValueError as error:
        print(f"Invalid configuration: {error}", file=sys.stderr)
        return 2


def seed_defaults(config: MonitorConfig) -> int:
    """Insert bundled monitor targets from config when they are not already stored."""

    gateway = detect_default_gateway()
    seed_targets = build_bundled_seed_targets(config, gateway)
    if not seed_targets:
        print("No bundled targets to seed.", file=sys.stderr)
        return 1

    store = StatusStore(config.db_path, config.storage_config)
    try:
        existing = len(store.list_targets())
        store.seed_targets(seed_targets)
        store.refresh_configured_seeds(seed_targets)
        for target in repair_api_health_targets(store.list_targets()):
            store.update_target(target.id, {"config": target.config, "host": target.host})
        total = len(store.list_targets())
        added = max(0, total - existing)
        print(f"Monitor targets ready ({total} configured, {added} newly added).")
    finally:
        store.close()

    return 0


def build_bundled_seed_targets(config: MonitorConfig, gateway: str | None) -> list:
    """Build default targets from config seeds, legacy ICMP defaults, and the local gateway."""

    seed_payloads = [
        target.to_dict() for target in build_targets(config.target_args, gateway, config.default_target_args)
    ]
    if not config.target_args:
        seed_payloads.extend(config.default_target_seeds)
    return [target_from_seed(target, config.interval_ms, config.timeout_ms) for target in seed_payloads]


def database_exists(db_path: str) -> bool:
    """Return True when the configured SQLite database file is already on disk."""

    if str(db_path) == ":memory:":
        return True
    return Path(db_path).expanduser().resolve().is_file()


def ensure_initialized(config: MonitorConfig) -> None:
    """Seed bundled defaults when setup has not created the database yet."""

    if database_exists(config.db_path):
        return

    print("Database not found; running first-time setup...", flush=True)
    exit_code = seed_defaults(config)
    if exit_code != 0:
        raise ValueError("first-time setup failed to seed monitor targets")


def apply_runtime_target_seeds(config: MonitorConfig, store: StatusStore, gateway: str | None) -> None:
    """Apply explicit CLI targets and sync an existing gateway without inserting bundled defaults."""

    if config.target_args:
        payloads = [target.to_dict() for target in build_targets(config.target_args, gateway, [])]
        runtime_targets = [target_from_seed(target, config.interval_ms, config.timeout_ms) for target in payloads]
        store.seed_targets(runtime_targets)
        return

    if not gateway:
        return

    existing = store.get_target("gateway")
    sync_payload = gateway_host_sync_payload(existing, gateway)
    if sync_payload:
        store.update_target("gateway", sync_payload)


def run(config: MonitorConfig) -> int:
    """Start the HTTP server and execute the sampling loop until stopped."""

    started_at = now_ms()
    gateway = detect_default_gateway()
    network = detect_network_identity(config.wifi_name)

    store = StatusStore(config.db_path, config.storage_config)
    apply_runtime_target_seeds(config, store, gateway)
    for target in repair_api_health_targets(store.list_targets()):
        store.update_target(target.id, {"config": target.config, "host": target.host})
    targets = store.list_targets()

    if not targets:
        print(
            "No monitor targets configured. Run `make setup` or `python backend/monitor.py seed` "
            "to add defaults, or pass --target 192.168.1.1:Router:gateway",
            file=sys.stderr,
        )
        store.close()
        return 1
    state = MonitorState(config, targets, network, started_at, store)
    static_dir = resolve_static_dir(config.static_dir, dev_mode=config.no_clear)

    try:
        server = StatusServer((config.host, config.port), StatusHandler, state, static_dir, config.security_headers)
    except OSError as error:
        store.close()
        if error.errno == errno.EADDRINUSE:
            print(f"Port {config.port} is already in use.", file=sys.stderr)
            print(f"Open the existing dashboard at http://localhost:{config.port}", file=sys.stderr)
            print(
                f"Or start another monitor with: python3 backend/monitor.py --port {config.port + 1}",
                file=sys.stderr,
            )
            return 1
        raise

    try:
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def stop(_signum: int | None = None, _frame: object | None = None) -> None:
            state.stopping.set()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        print_startup(config, targets)
        ends_at = started_at + config.duration_ms if config.duration_ms is not None else None
        scheduler = TargetScheduler(state, max_workers=max(1, min(16, len(targets))))
        scheduler.run(
            ends_at,
            render=None if config.no_clear else lambda summary: render_dashboard(summary, config),
        )
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
        store.close()

    dev_mode = os.environ.get("NETBOX_DEV_MODE") == "1"
    if not dev_mode and not config.no_clear and state.last_summary:
        render_dashboard(state.last_summary, config)
    if not dev_mode:
        print(f"\nFinished after {format_duration(now_ms() - started_at)}. Bye, router whisperer.")
    return 0


def parse_args(argv: list[str] | None = None) -> MonitorConfig:
    """Parse and validate command-line options into a monitor config."""

    load_env_files(PROJECT_ROOT)
    backend_config = load_json_config("backend.json")
    security_config = load_security_config()
    speed_config = load_speed_config()
    storage_config = load_storage_config()
    allowed_bind_hosts = list(security_config["allowedBindHosts"])
    default_target_args = load_default_target_args()
    default_host = env_str("NETBOX_HOST", nested(backend_config, "server", "host", default="127.0.0.1"))
    default_port = env_int("NETBOX_PORT", nested(backend_config, "server", "port", default=4177))
    default_static_dir = env_str(
        "NETBOX_STATIC_DIR",
        nested(backend_config, "server", "staticDir", default=None),
    )
    default_duration = env_str("NETBOX_DURATION", nested(backend_config, "monitor", "duration", default=None))
    default_interval = env_str("NETBOX_INTERVAL", nested(backend_config, "monitor", "interval", default="1s"))
    default_timeout = env_str("NETBOX_TIMEOUT", nested(backend_config, "monitor", "timeout", default="900ms"))
    default_db_path = env_str(
        "NETBOX_DB_PATH",
        nested(backend_config, "storage", "dbPath", default=str(DEFAULT_DB_PATH)),
    )

    parser = argparse.ArgumentParser(description="Netbox terminal-first network status monitor.")
    parser.add_argument(
        "--duration",
        default=default_duration,
        help="Optional run length, e.g. 2h, 30m, 90s. Defaults to indefinite.",
    )
    parser.add_argument("--interval", default=default_interval, help="Check interval, e.g. 1s.")
    parser.add_argument("--timeout", default=default_timeout, help="Ping timeout, e.g. 900ms.")
    parser.add_argument("--host", default=default_host, help="Bind host. Defaults to localhost only.")
    parser.add_argument("--port", type=int, default=default_port, help="Web status page port.")
    parser.add_argument(
        "--latency-warn",
        type=float,
        default=env_float("NETBOX_LATENCY_WARN_MS", nested(backend_config, "monitor", "latencyWarnMs", default=150)),
        help="Latency warning threshold in ms.",
    )
    parser.add_argument("--target", action="append", default=[], help="Target as host:label:scope.")
    parser.add_argument("--targets", default=env_str("NETBOX_TARGETS", ""), help="Comma-separated target list.")
    parser.add_argument(
        "--wifi-name",
        default=env_str("NETBOX_WIFI_NAME", nested(backend_config, "network", "wifiName", default="")),
        help="Override the displayed Wi-Fi network name/SSID.",
    )
    parser.add_argument("--db-path", default=default_db_path, help="SQLite database path.")
    parser.add_argument("--static-dir", default=default_static_dir, help="Override frontend static directory.")
    parser.add_argument(
        "--no-clear",
        action="store_true",
        default=env_bool("NETBOX_NO_CLEAR", nested(backend_config, "monitor", "noClear", default=False)),
        help="Do not redraw the terminal screen.",
    )
    parser.add_argument(
        "--failures-to-degrade",
        type=int,
        default=env_int(
            "NETBOX_FAILURES_TO_DEGRADE",
            nested(backend_config, "monitor", "failuresToDegrade", default=1),
        ),
    )
    parser.add_argument(
        "--failures-to-down",
        type=int,
        default=env_int("NETBOX_FAILURES_TO_DOWN", nested(backend_config, "monitor", "failuresToDown", default=3)),
    )
    parser.add_argument(
        "--high-latency-to-degrade",
        type=int,
        default=env_int(
            "NETBOX_HIGH_LATENCY_TO_DEGRADE",
            nested(backend_config, "monitor", "highLatencyToDegrade", default=2),
        ),
    )
    parser.add_argument(
        "--recent-window",
        type=int,
        default=env_int("NETBOX_RECENT_WINDOW", nested(backend_config, "monitor", "recentWindow", default=5)),
    )
    parser.add_argument(
        "--history-points",
        type=int,
        default=env_int("NETBOX_HISTORY_POINTS", nested(backend_config, "monitor", "historyPoints", default=90)),
        help="Recent checks shown as web UI bars.",
    )
    parser.add_argument(
        "--retention-points",
        type=int,
        default=env_int(
            "NETBOX_RETENTION_POINTS",
            nested(backend_config, "monitor", "retentionPoints", default=86_400),
        ),
        help="Maximum samples retained in memory for indefinite runs.",
    )
    args = parser.parse_args(argv)

    target_args = list(args.target)
    if args.targets:
        target_args.extend([target.strip() for target in args.targets.split(",") if target.strip()])

    duration_ms = parse_duration(args.duration) if args.duration else None
    interval_ms = parse_duration(args.interval)
    timeout_ms = parse_duration(args.timeout)

    if duration_ms is not None and duration_ms < 1_000:
        raise ValueError("duration must be at least 1s")
    if not 250 <= interval_ms <= 60_000:
        raise ValueError("interval must be between 250ms and 60s")
    if not 100 <= timeout_ms <= 30_000:
        raise ValueError("timeout must be between 100ms and 30s")
    if args.failures_to_down < args.failures_to_degrade:
        raise ValueError("failures-to-down must be greater than or equal to failures-to-degrade")
    if args.history_points < 1 or args.history_points > 300:
        raise ValueError("history-points must be between 1 and 300")
    if args.retention_points < args.history_points:
        raise ValueError("retention-points must be greater than or equal to history-points")

    return MonitorConfig(
        duration_ms=duration_ms,
        interval_ms=interval_ms,
        timeout_ms=timeout_ms,
        port=validate_port(args.port),
        host=validate_bind_host(args.host, allowed_bind_hosts),
        latency_warn_ms=args.latency_warn,
        failures_to_degrade=args.failures_to_degrade,
        failures_to_down=args.failures_to_down,
        high_latency_to_degrade=args.high_latency_to_degrade,
        recent_window=args.recent_window,
        history_points=args.history_points,
        retention_points=args.retention_points,
        no_clear=args.no_clear,
        wifi_name=args.wifi_name,
        db_path=resolve_project_path(args.db_path) or str(DEFAULT_DB_PATH),
        target_args=target_args,
        default_target_args=default_target_args,
        default_target_seeds=load_default_target_seeds(),
        security_headers={str(key): str(value) for key, value in security_config["headers"].items()},
        speed_config=speed_config,
        storage_config=storage_config,
        static_dir=resolve_project_path(args.static_dir),
    )


def resolve_static_dir(override: str | None, *, dev_mode: bool = False) -> Path:
    """Return the directory used for production static asset serving."""

    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"static-dir does not exist: {path}")
        return path

    if DEFAULT_STATIC_DIR.is_dir():
        return DEFAULT_STATIC_DIR

    if dev_mode:
        return ensure_dev_static_dir()

    raise ValueError("frontend/dist does not exist. Run `make build` or pass --static-dir.")


def ensure_dev_static_dir() -> Path:
    """Create a tiny placeholder static dir for API-only development runs."""

    dev_static = PROJECT_ROOT / ".dev" / "static"
    dev_static.mkdir(parents=True, exist_ok=True)
    index = dev_static / "index.html"
    if not index.exists():
        index.write_text(
            "<!doctype html><html><head><title>Netbox</title></head>"
            "<body><p>Development mode: open the Vite dev server for the dashboard UI.</p></body></html>",
            encoding="utf-8",
        )
    return dev_static
