#!/usr/bin/env python3
"""Development runner for backend auto-reload and Vite HMR."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_WATCH_PATHS = [ROOT / "backend" / "monitor.py", ROOT / "backend" / "src"]
RESTART_GRACE_SECONDS = 2.0
BACKEND_SHUTDOWN_TIMEOUT_SECONDS = 8.0
SQLITE_UNLOCK_TIMEOUT_SECONDS = 6.0
BACKEND_RESTART_ATTEMPTS = 3


def main() -> int:
    """Start frontend and backend dev processes and watch Python files."""

    load_env_files()
    frontend_config = load_frontend_config()
    parser = argparse.ArgumentParser(description="Run backend auto-reload plus Vite frontend HMR.")
    parser.add_argument("--host", default=setting("NETBOX_HOST", frontend_config.get("devServer", {}).get("host", "127.0.0.1")))
    parser.add_argument("--backend-port", type=int, default=int(setting("NETBOX_PORT", frontend_config.get("api", {}).get("backendPort", 4177))))
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=int(setting("NETBOX_FRONTEND_PORT", frontend_config.get("devServer", {}).get("port", 5177))),
    )
    parser.add_argument("backend_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    backend_args = args.backend_args[1:] if args.backend_args[:1] == ["--"] else args.backend_args
    ensure_runtime_dirs()

    print()
    print("Starting Netbox dev stack...")
    print(f"  Dashboard  http://{args.host}:{args.frontend_port}")
    print(f"  API        http://{args.host}:{args.backend_port}/api/status")
    print("  Backend restarts on Python changes; frontend updates through Vite HMR.")
    print("  Press Ctrl+C to stop both processes.")
    print(flush=True)

    assert_backend_port_available(args.host, args.backend_port)

    frontend = start_frontend(args.host, args.frontend_port, args.backend_port)
    backend = start_backend_with_retries(args.host, args.backend_port, backend_args)
    last_signature = backend_signature()
    backend_started_at = time.monotonic()

    stopping = False

    def stop(_signum: int | None = None, _frame: object | None = None) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    try:
        while not stopping:
            time.sleep(0.7)

            if frontend.poll() is not None:
                print("Frontend dev server exited.", file=sys.stderr)
                return frontend.returncode or 1

            signature = backend_signature()
            if signature != last_signature and time.monotonic() - backend_started_at >= RESTART_GRACE_SECONDS:
                print("Backend change detected; restarting monitor...", flush=True)
                backend = restart_backend(args.host, args.backend_port, backend_args, backend)
                last_signature = signature
                backend_started_at = time.monotonic()
            elif backend.poll() is not None:
                code = backend.returncode or 1
                print(
                    f"Backend monitor exited with code {code}; restarting...",
                    file=sys.stderr,
                    flush=True,
                )
                backend = restart_backend(args.host, args.backend_port, backend_args, backend)
                last_signature = backend_signature()
                backend_started_at = time.monotonic()
    finally:
        stop_process(backend)
        stop_process(frontend)

    return 0


def ensure_runtime_dirs() -> None:
    """Create local runtime folders used by dev and SQLite persistence."""

    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / ".dev" / "static").mkdir(parents=True, exist_ok=True)


def restart_backend(
    host: str,
    port: int,
    extra_args: list[str],
    process: subprocess.Popen[bytes],
) -> subprocess.Popen[bytes]:
    """Stop the current monitor and start a fresh process once the port is free."""

    stop_process(process, timeout=BACKEND_SHUTDOWN_TIMEOUT_SECONDS)
    wait_for_port_free(host, port)
    if port_is_open(host, port):
        print_port_conflict(host, port)
        raise SystemExit(1)
    wait_for_sqlite_available(resolve_dev_db_path(), SQLITE_UNLOCK_TIMEOUT_SECONDS)
    return start_backend_with_retries(host, port, extra_args)


def start_backend(host: str, port: int, extra_args: list[str]) -> subprocess.Popen[bytes]:
    """Start the monitor backend with repository-local Python imports."""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend" / "src")
    env["PYTHONUNBUFFERED"] = "1"
    env["NETBOX_DEV_MODE"] = "1"
    command = [
        sys.executable,
        "-B",
        str(ROOT / "backend" / "monitor.py"),
        "--host",
        host,
        "--port",
        str(port),
        "--no-clear",
        *extra_args,
    ]
    return subprocess.Popen(command, cwd=ROOT, env=env)


def start_frontend(host: str, port: int, backend_port: int) -> subprocess.Popen[bytes]:
    """Start the Vite development server."""

    npm = shlex.split(os.environ.get("NPM", "npm"))
    env = os.environ.copy()
    env["NETBOX_HOST"] = host
    env["NETBOX_PORT"] = str(backend_port)
    env["NETBOX_FRONTEND_HOST"] = host
    env["NETBOX_FRONTEND_PORT"] = str(port)
    command = [
        *npm,
        "run",
        "dev",
        "--",
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.Popen(command, cwd=ROOT / "frontend", env=env)


def load_env_files() -> None:
    """Load root dotenv files for the dev stack without overriding shell values."""

    original_keys = set(os.environ)
    load_env_file(ROOT / ".env", original_keys)
    load_env_file(ROOT / ".env.local", original_keys)
    environment = os.environ.get("NETBOX_ENV", "development").strip() or "development"
    load_env_file(ROOT / f".env.{environment}", original_keys)
    load_env_file(ROOT / f".env.{environment}.local", original_keys)


def load_env_file(path: Path, original_keys: set[str]) -> None:
    if not path.is_file():
        return

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in original_keys:
            os.environ[key] = value.strip().strip('"').strip("'")


def load_frontend_config() -> dict[str, object]:
    config_dir = Path(os.environ.get("NETBOX_CONFIG_DIR", "config")).expanduser()
    if not config_dir.is_absolute():
        config_dir = ROOT / config_dir
    config_path = config_dir / "frontend.json"
    if not config_path.is_file():
        return {}
    with config_path.open() as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def setting(name: str, default: object) -> str:
    value = os.environ.get(name)
    return str(default if value is None or value == "" else value)


def backend_signature() -> tuple[tuple[str, int, int], ...]:
    """Return a cheap file signature for backend hot-reload detection."""

    files: list[Path] = []
    for path in BACKEND_WATCH_PATHS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*.py") if "__pycache__" not in candidate.parts)

    return tuple(sorted((str(path.relative_to(ROOT)), path.stat().st_mtime_ns, path.stat().st_size) for path in files))


def resolve_dev_db_path() -> Path:
    """Return the SQLite path used by the dev backend."""

    raw_path = os.environ.get("NETBOX_DB_PATH", "data/netbox.sqlite3")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def wait_for_sqlite_available(db_path: Path, timeout: float) -> None:
    """Wait until the dev SQLite database can be opened again."""

    if not db_path.is_file():
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            import sqlite3

            connection = sqlite3.connect(db_path, timeout=1)
            connection.execute("PRAGMA busy_timeout = 1000")
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()
            connection.close()
            return
        except Exception:
            time.sleep(0.15)


def start_backend_with_retries(host: str, port: int, extra_args: list[str]) -> subprocess.Popen[bytes]:
    """Start the backend, retrying briefly when SQLite is still locked."""

    last_process: subprocess.Popen[bytes] | None = None
    for attempt in range(BACKEND_RESTART_ATTEMPTS):
        if attempt:
            wait_for_sqlite_available(resolve_dev_db_path(), SQLITE_UNLOCK_TIMEOUT_SECONDS)
        last_process = start_backend(host, port, extra_args)
        time.sleep(0.4)
        if last_process.poll() is None:
            return last_process
    if last_process is None:
        raise SystemExit(1)
    return last_process


def stop_process(process: subprocess.Popen[bytes], timeout: float = 5.0) -> None:
    """Terminate a child process, escalating to kill after a short timeout."""

    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)


def port_is_open(host: str, port: int) -> bool:
    """Return True when something is accepting TCP connections on host:port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def describe_port_conflict(host: str, port: int) -> str:
    """Return a short description of which process is listening on the backend port."""

    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if len(lines) > 1:
            return "\n".join(lines)
    except FileNotFoundError:
        pass

    return f"Port {port} is already in use on {host}."


def print_port_conflict(host: str, port: int) -> None:
    """Print a helpful message when the backend port is unavailable."""

    print(describe_port_conflict(host, port), file=sys.stderr)
    print(
        f"\nStop the process using port {port}, then run make run again.",
        file=sys.stderr,
    )
    print(f"Example: lsof -ti tcp:{port} | xargs kill", file=sys.stderr)


def assert_backend_port_available(host: str, port: int) -> None:
    """Fail fast when another process is already bound to the backend port."""

    if not port_is_open(host, port):
        return

    print_port_conflict(host, port)
    raise SystemExit(1)


def wait_for_port_free(host: str, port: int, timeout: float = 5.0) -> None:
    """Wait until the backend port is available for a replacement process."""

    deadline = time.monotonic() + timeout
    while port_is_open(host, port) and time.monotonic() < deadline:
        time.sleep(0.1)


if __name__ == "__main__":
    raise SystemExit(main())
