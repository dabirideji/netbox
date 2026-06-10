#!/usr/bin/env python3
"""Development runner for backend auto-reload and Vite HMR."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_WATCH_PATHS = [ROOT / "backend" / "monitor.py", ROOT / "backend" / "src"]
RESTART_GRACE_SECONDS = 2.0


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

    frontend = start_frontend(args.host, args.frontend_port, args.backend_port)
    backend = start_backend(args.host, args.backend_port, backend_args)
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
                stop_process(backend)
                backend = start_backend(args.host, args.backend_port, backend_args)
                last_signature = signature
                backend_started_at = time.monotonic()
            elif backend.poll() is not None:
                print("Backend monitor exited; waiting for file change to restart.", file=sys.stderr)
    finally:
        stop_process(backend)
        stop_process(frontend)

    return 0


def ensure_runtime_dirs() -> None:
    """Create local runtime folders used by dev and SQLite persistence."""

    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / ".dev" / "static").mkdir(parents=True, exist_ok=True)


def start_backend(host: str, port: int, extra_args: list[str]) -> subprocess.Popen[bytes]:
    """Start the monitor backend with repository-local Python imports."""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend" / "src")
    env["PYTHONUNBUFFERED"] = "1"
    env["NETBOX_DEV_MODE"] = "1"
    command = [
        sys.executable,
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


def stop_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate a child process, escalating to kill after a short timeout."""

    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
