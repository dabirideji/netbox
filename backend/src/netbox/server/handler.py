"""HTTP request handler for JSON APIs, SSE, and static assets."""

from __future__ import annotations

import json
import mimetypes
import queue
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from netbox.core.responses import HttpStatus, api_error_body, api_error_code_for_message
from netbox.server.app import StatusServer
from netbox.server.api_docs import DOCS_CSP, dispatch_api_docs_get
from netbox.server.dispatch import dispatch_delete, dispatch_get, dispatch_patch, dispatch_post
from netbox.server.static_files import is_within


class StatusHandler(BaseHTTPRequestHandler):
    """Request handler for JSON APIs, SSE, and built frontend assets."""

    server_version = "Netbox/1.0"
    max_json_body_bytes = 65_536

    @property
    def app_server(self) -> StatusServer:
        """Return the concrete server type with application attributes."""

        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:
        """Route GET requests to API endpoints, SSE, or static assets."""

        parsed_url = urlparse(self.path)

        if dispatch_api_docs_get(self, parsed_url):
            return

        try:
            if dispatch_get(self, parsed_url):
                return
        except ValueError as error:
            self.write_error(str(error))
            return
        except Exception as error:
            self.write_error(str(error) or "Internal server error", status=HttpStatus.BAD_REQUEST)
            return

        if parsed_url.path == "/events":
            self.stream_events()
            return

        self.serve_static(parsed_url.path)

    def do_POST(self) -> None:
        """Route JSON POST requests to write APIs."""

        route = urlparse(self.path).path

        try:
            if dispatch_post(self, route):
                return
        except ValueError as error:
            self.write_error(str(error))
            return
        except Exception as error:
            self.write_error(str(error) or "Internal server error", status=HttpStatus.BAD_REQUEST)
            return

        self.send_error(HttpStatus.NOT_FOUND, "Not found")

    def do_PATCH(self) -> None:
        """Route JSON PATCH requests to merge APIs."""

        route = urlparse(self.path).path

        try:
            if dispatch_patch(self, route):
                return
        except ValueError as error:
            self.write_error(str(error))
            return
        except Exception as error:
            self.write_error(str(error) or "Internal server error", status=HttpStatus.BAD_REQUEST)
            return

        self.send_error(HttpStatus.NOT_FOUND, "Not found")

    def do_DELETE(self) -> None:
        """Route JSON DELETE requests to destructive APIs."""

        route = urlparse(self.path).path

        try:
            if dispatch_delete(self, route):
                return
        except ValueError as error:
            self.write_error(str(error))
            return
        except Exception as error:
            self.write_error(str(error) or "Internal server error", status=HttpStatus.BAD_REQUEST)
            return

        self.send_error(HttpStatus.NOT_FOUND, "Not found")

    def write_error(self, message: str, status: int = HttpStatus.BAD_REQUEST, code: str | None = None) -> None:
        """Write a structured JSON error payload with a stable response code."""

        resolved_code = code or api_error_code_for_message(message, status)
        self.write_json(api_error_body(resolved_code, message), status=status)

    def write_json(self, payload: dict[str, Any], status: int = HttpStatus.OK) -> None:
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

        self.send_response(HttpStatus.OK)
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

    def serve_path_file(self, path: Path, content_type: str, *, docs_csp: bool = False) -> None:
        """Serve one file from disk with standard security headers."""

        if not path.is_file():
            self.send_error(HttpStatus.NOT_FOUND, "Not found")
            return

        body = path.read_bytes()
        self.send_response(HttpStatus.OK)
        self.add_default_headers(docs_csp=docs_csp)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, route: str) -> None:
        """Serve frontend assets while preventing path traversal."""

        requested = "/index.html" if route == "/" else route
        static_dir = self.app_server.static_dir
        candidate = (static_dir / requested.lstrip("/")).resolve()

        if not is_within(candidate, static_dir) or not candidate.is_file():
            candidate = static_dir / "index.html"
            if route.startswith("/api/") or not candidate.is_file():
                self.send_error(HttpStatus.NOT_FOUND, "Not found")
                return

        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate)[0] or "application/octet-stream"
        self.send_response(HttpStatus.OK)
        self.add_default_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def add_default_headers(self, *, docs_csp: bool = False) -> None:
        """Attach conservative browser security headers to every response."""

        for header, value in self.app_server.security_headers.items():
            if docs_csp and header == "Content-Security-Policy":
                self.send_header(header, DOCS_CSP)
                continue
            self.send_header(header, value)

    def log_message(self, _format: str, *_args: Any) -> None:
        return
