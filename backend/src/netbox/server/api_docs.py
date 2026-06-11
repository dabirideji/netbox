"""Serve the OpenAPI spec and bundled Swagger UI documentation."""

from __future__ import annotations

import mimetypes
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import ParseResult

from netbox.core.responses import HttpStatus
from netbox.server.static_files import is_within

if TYPE_CHECKING:
    from netbox.server.handler import StatusHandler

DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'"
)


def src_root() -> Path:
    """Return the backend ``src`` directory in development or the PyInstaller bundle root."""

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def openapi_path() -> Path:
    return src_root() / "openapi.yaml"


def docs_root() -> Path:
    return src_root() / "docs"


def dispatch_api_docs_get(handler: StatusHandler, parsed_url: ParseResult) -> bool:
    """Serve ``/api/openapi.yaml`` and ``/api/docs`` when the route matches."""

    route = parsed_url.path.rstrip("/") or "/"

    if route in {"/api/openapi.yaml", "/openapi.yaml"}:
        handler.serve_path_file(openapi_path(), "application/yaml; charset=utf-8")
        return True

    if route == "/api/docs":
        handler.serve_path_file(docs_root() / "index.html", "text/html; charset=utf-8", docs_csp=True)
        return True

    prefix = "/api/docs/"
    if route.startswith(prefix):
        relative = route[len(prefix) :]
        candidate = (docs_root() / relative).resolve()
        if not is_within(candidate, docs_root()) or not candidate.is_file():
            handler.send_error(HttpStatus.NOT_FOUND, "Not found")
            return True
        content_type = mimetypes.guess_type(candidate)[0] or "application/octet-stream"
        handler.serve_path_file(candidate, content_type, docs_csp=True)
        return True

    return False
