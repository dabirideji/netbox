"""HTTP API, static file, and server-sent event handling."""

from __future__ import annotations

import json
import mimetypes
import queue
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from netbox.state import MonitorState
from netbox.wallpaper import fetch_wallpaper

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; connect-src 'self' https://locate.measurementlab.net wss:; "
        "script-src 'self'; worker-src 'self'; style-src 'self'; "
        "img-src 'self' data: https://images.pexels.com; base-uri 'none'; frame-ancestors 'none'"
    ),
}


class StatusServer(ThreadingHTTPServer):
    """Threaded HTTP server carrying monitor state and static asset paths."""

    daemon_threads = True
    block_on_close = False

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        state: MonitorState,
        static_dir: Path,
        security_headers: dict[str, str] | None = None,
    ) -> None:
        self.state = state
        self.static_dir = static_dir.resolve()
        self.security_headers = security_headers or SECURITY_HEADERS
        super().__init__(server_address, handler_class)

    def handle_error(self, request: object, client_address: tuple[str, int]) -> None:
        """Suppress expected browser disconnect noise from long-lived SSE."""

        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


class StatusHandler(BaseHTTPRequestHandler):
    """Request handler for JSON APIs, SSE, and built frontend assets."""

    server_version = "Netbox/1.0"
    max_json_body_bytes = 16_384

    @property
    def app_server(self) -> StatusServer:
        """Return the concrete server type with application attributes."""

        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:
        """Route GET requests to API endpoints, SSE, or static assets."""

        parsed_url = urlparse(self.path)
        route = parsed_url.path

        try:
            if route == "/api/status":
                self.write_json(self.app_server.state.snapshot())
                return

            if route == "/api/history":
                query = parse_query(parsed_url.query)
                self.write_json(
                    self.app_server.state.history(
                        query["points"],
                        query["from"],
                        query["to"],
                    )
                )
                return

            if route == "/api/targets/history":
                query = parse_query(parsed_url.query)
                self.write_json(
                    self.app_server.state.target_history(
                        query["points"],
                        query["from"],
                        query["to"],
                    )
                )
                return

            if route == "/api/events":
                query = parse_query(parsed_url.query)
                self.write_json(
                    self.app_server.state.persisted_events(
                        query["limit"],
                        query["from"],
                        query["to"],
                        query["offset"],
                    )
                )
                return

            if route == "/api/speed-tests":
                query = parse_query(parsed_url.query)
                self.write_json(
                    self.app_server.state.speed_tests(
                        query["limit"],
                        query["from"],
                        query["to"],
                        query["offset"],
                    )
                )
                return

            if route == "/api/preferences":
                self.write_json(self.app_server.state.preferences())
                return

            if route == "/api/storage":
                self.write_json(self.app_server.state.storage_stats())
                return

            if route == "/api/wallpaper":
                self.write_json(fetch_wallpaper())
                return
        except ValueError as error:
            self.write_json({"error": str(error)}, status=400)
            return

        if route == "/events":
            self.stream_events()
            return

        self.serve_static(route)

    def do_POST(self) -> None:
        """Route JSON POST requests to write APIs."""

        parsed_url = urlparse(self.path)
        route = parsed_url.path

        try:
            if route == "/api/speed-tests":
                self.write_json(self.app_server.state.record_speed_test(self.read_json_body()), status=201)
                return

            if route == "/api/storage/clear":
                payload = self.read_json_body()
                scope = payload.get("scope")
                if not isinstance(scope, str):
                    raise ValueError("scope is required")
                self.write_json(self.app_server.state.clear_storage(scope))
                return
        except ValueError as error:
            self.write_json({"error": str(error)}, status=400)
            return

        self.send_error(404, "Not found")

    def do_PATCH(self) -> None:
        """Route JSON PATCH requests to merge APIs."""

        parsed_url = urlparse(self.path)
        route = parsed_url.path

        try:
            if route == "/api/preferences":
                self.write_json(
                    self.app_server.state.update_preferences(self.read_json_body()),
                )
                return
        except ValueError as error:
            self.write_json({"error": str(error)}, status=400)
            return

        self.send_error(404, "Not found")

    def write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        """Write a JSON response with security and no-store headers."""

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.add_default_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict[str, Any]:
        """Read a bounded JSON object request body."""

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Content-Length must be an integer") from None
        if content_length <= 0:
            raise ValueError("request body is required")
        if content_length > self.max_json_body_bytes:
            raise ValueError("request body is too large")

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            raise ValueError("request body must be valid JSON") from None
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def stream_events(self) -> None:
        """Stream live monitor updates as server-sent events."""

        self.send_response(200)
        self.add_default_headers()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        client = self.app_server.state.add_client()
        try:
            while not self.app_server.state.stopping.is_set():
                try:
                    message = client.get(timeout=15)
                except queue.Empty:
                    message = ": heartbeat\n\n"
                self.wfile.write(message.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.app_server.state.remove_client(client)

    def serve_static(self, route: str) -> None:
        """Serve frontend assets while preventing path traversal."""

        requested = "/index.html" if route == "/" else route
        static_dir = self.app_server.static_dir
        candidate = (static_dir / requested.lstrip("/")).resolve()

        if not is_within(candidate, static_dir) or not candidate.is_file():
            candidate = static_dir / "index.html"
            if route.startswith("/api/") or not candidate.is_file():
                self.send_error(404, "Not found")
                return

        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate)[0] or "application/octet-stream"
        self.send_response(200)
        self.add_default_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def add_default_headers(self) -> None:
        """Attach conservative browser security headers to every response."""

        for header, value in self.app_server.security_headers.items():
            self.send_header(header, value)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def is_within(path: Path, parent: Path) -> bool:
    """Return whether `path` resolves inside `parent`."""

    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def parse_query(query: str) -> dict[str, int | None]:
    """Parse and bound API query parameters shared by history endpoints."""

    params = parse_qs(query)
    from_ms = parse_optional_int(params, "from", min_value=0)
    to_ms = parse_optional_int(params, "to", min_value=0)
    if from_ms is not None and to_ms is not None and from_ms > to_ms:
        raise ValueError("from must be less than or equal to to")

    return {
        "from": from_ms,
        "to": to_ms,
        "points": parse_bounded_int(params, "points", default=360, min_value=1, max_value=2_000),
        "limit": parse_bounded_int(params, "limit", default=50, min_value=1, max_value=500),
        "offset": parse_bounded_int(params, "offset", default=0, min_value=0, max_value=100_000),
    }


def parse_bounded_int(
    params: dict[str, list[str]],
    name: str,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    """Parse an integer query parameter constrained to an inclusive range."""

    raw_value = params.get(name, [str(default)])[0]
    try:
        value = int(raw_value)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")
    return value


def parse_optional_int(params: dict[str, list[str]], name: str, min_value: int) -> int | None:
    """Parse an optional integer query parameter with a lower bound."""

    raw_values = params.get(name)
    if not raw_values or raw_values[0] == "":
        return None
    try:
        value = int(raw_values[0])
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
    if value < min_value:
        raise ValueError(f"{name} must be greater than or equal to {min_value}")
    return value
