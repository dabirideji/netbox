"""Threaded HTTP server for the monitor API."""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from netbox.server.constants import SECURITY_HEADERS
from netbox.state import MonitorState


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
