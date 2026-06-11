"""Central registry for API payloads, monitor statuses, and response codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

Status: TypeAlias = Literal["operational", "degraded", "down", "unknown"]
SpeedTestStatus: TypeAlias = Literal["completed", "failed"]
IncidentStatus: TypeAlias = Literal["open", "resolved"]
StreamEventType: TypeAlias = Literal["status", "event", "targets", "speedTest", "alert"]
StorageClearScope: TypeAlias = Literal["incidents", "ping", "speedTests", "all"]

MONITOR_STATUS_KEYS: tuple[Status, ...] = ("operational", "degraded", "down", "unknown")
SPEED_TEST_STATUS_KEYS: tuple[SpeedTestStatus, ...] = ("completed", "failed")
INCIDENT_STATUS_KEYS: tuple[IncidentStatus, ...] = ("open", "resolved")
STREAM_EVENT_KEYS: tuple[StreamEventType, ...] = ("status", "event", "targets", "speedTest", "alert")
STORAGE_CLEAR_SCOPE_KEYS: tuple[StorageClearScope, ...] = ("incidents", "ping", "speedTests", "all")


@dataclass(frozen=True)
class StatusDefinition:
    """Machine-readable status metadata shared by API, storage, and UI layers."""

    key: str
    code: str
    severity: int
    label: str
    terminal_symbol: str


@dataclass(frozen=True)
class ApiErrorDefinition:
    """Stable API error code with a default HTTP status."""

    code: str
    http_status: int
    label: str


class HttpStatus:
    """HTTP statuses used by the local JSON API."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    NOT_FOUND = 404


MONITOR_STATUSES: dict[Status, StatusDefinition] = {
    "operational": StatusDefinition("operational", "MON-000", 0, "Operational", "●"),
    "degraded": StatusDefinition("degraded", "MON-110", 1, "Degraded", "▲"),
    "down": StatusDefinition("down", "MON-120", 2, "Down", "■"),
    "unknown": StatusDefinition("unknown", "MON-900", 0, "Unknown", "○"),
}

SPEED_TEST_STATUSES: dict[SpeedTestStatus, StatusDefinition] = {
    "completed": StatusDefinition("completed", "SPD-000", 0, "Completed", "●"),
    "failed": StatusDefinition("failed", "SPD-100", 1, "Failed", "■"),
}

INCIDENT_STATUSES: dict[IncidentStatus, StatusDefinition] = {
    "open": StatusDefinition("open", "INC-100", 1, "Open", "▲"),
    "resolved": StatusDefinition("resolved", "INC-000", 0, "Resolved", "●"),
}

STREAM_EVENT_TYPES: dict[StreamEventType, StatusDefinition] = {
    "status": StatusDefinition("status", "SSE-001", 0, "Status", ""),
    "event": StatusDefinition("event", "SSE-002", 0, "Event", ""),
    "targets": StatusDefinition("targets", "SSE-003", 0, "Targets", ""),
    "speedTest": StatusDefinition("speedTest", "SSE-004", 0, "Speed test", ""),
    "alert": StatusDefinition("alert", "SSE-005", 0, "Alert", ""),
}

STORAGE_CLEAR_SCOPES: dict[StorageClearScope, StatusDefinition] = {
    "incidents": StatusDefinition("incidents", "STG-001", 0, "Incidents", ""),
    "ping": StatusDefinition("ping", "STG-002", 0, "Ping samples", ""),
    "speedTests": StatusDefinition("speedTests", "STG-003", 0, "Speed tests", ""),
    "all": StatusDefinition("all", "STG-900", 0, "All persisted data", ""),
}

API_ERRORS: dict[str, ApiErrorDefinition] = {
    "API-4000": ApiErrorDefinition("API-4000", HttpStatus.BAD_REQUEST, "Validation error"),
    "API-4001": ApiErrorDefinition("API-4001", HttpStatus.BAD_REQUEST, "Invalid query range"),
    "API-4002": ApiErrorDefinition("API-4002", HttpStatus.BAD_REQUEST, "Invalid query parameter"),
    "API-4003": ApiErrorDefinition("API-4003", HttpStatus.BAD_REQUEST, "Invalid request body"),
    "API-4004": ApiErrorDefinition("API-4004", HttpStatus.BAD_REQUEST, "Invalid storage scope"),
    "API-4005": ApiErrorDefinition("API-4005", HttpStatus.BAD_REQUEST, "Invalid speed test payload"),
    "API-4006": ApiErrorDefinition("API-4006", HttpStatus.BAD_REQUEST, "Invalid target payload"),
    "API-4007": ApiErrorDefinition("API-4007", HttpStatus.BAD_REQUEST, "Wallpaper unavailable"),
    "API-4008": ApiErrorDefinition("API-4008", HttpStatus.BAD_REQUEST, "Invalid alert payload"),
    "API-4009": ApiErrorDefinition("API-4009", HttpStatus.BAD_REQUEST, "Invalid SMTP payload"),
    "API-4040": ApiErrorDefinition("API-4040", HttpStatus.NOT_FOUND, "Resource not found"),
    "API-5030": ApiErrorDefinition("API-5030", HttpStatus.BAD_REQUEST, "Storage unavailable"),
}

STATUS_SEVERITY: dict[str, int] = {key: item.severity for key, item in MONITOR_STATUSES.items()}
VALID_SPEED_STATUSES = frozenset(SPEED_TEST_STATUS_KEYS)
STORAGE_CLEAR_SCOPE_VALUES = frozenset(STORAGE_CLEAR_SCOPE_KEYS)

_API_ERROR_MESSAGE_CODES: dict[str, str] = {
    "from must be less than or equal to to": "API-4001",
    "scope is required": "API-4004",
    "scope must be one of incidents, ping, speedTests, or all": "API-4004",
    "request body is required": "API-4003",
    "request body must be valid JSON": "API-4003",
    "request body must be a JSON object": "API-4003",
    "request body is too large": "API-4003",
    "Content-Length must be an integer": "API-4003",
    "preferences payload must be a JSON object": "API-4003",
    "speed test status must be completed or failed": "API-4005",
    "target was not found": "API-4040",
    "PEXELS_API_KEY is not configured": "API-4007",
    "speed tests are disabled": "API-5030",
    "target storage is unavailable": "API-5030",
    "log storage is unavailable": "API-5030",
    "preference storage is unavailable": "API-5030",
    "speed test storage is unavailable": "API-5030",
}


def monitor_status_definition(status: str) -> StatusDefinition:
    """Return monitor status metadata, defaulting to unknown."""

    return MONITOR_STATUSES.get(status, MONITOR_STATUSES["unknown"])  # type: ignore[arg-type]


def monitor_status_severity(status: str) -> int:
    """Return the persisted numeric severity for a monitor status key."""

    return monitor_status_definition(status).severity


def monitor_status_code(status: str) -> str:
    """Return the stable monitor status code for a status key."""

    return monitor_status_definition(status).code


def normalize_monitor_status(status: str) -> Status:
    """Return a supported monitor status key."""

    if status in MONITOR_STATUSES:
        return status  # type: ignore[return-value]
    return "unknown"


def speed_test_status_code(status: str) -> str:
    """Return the stable speed-test status code."""

    if status in SPEED_TEST_STATUSES:
        return SPEED_TEST_STATUSES[status].code  # type: ignore[index]
    return "SPD-900"


def incident_status_code(status: str) -> str:
    """Return the stable incident status code."""

    if status in INCIDENT_STATUSES:
        return INCIDENT_STATUSES[status].code  # type: ignore[index]
    return "INC-900"


def stream_event_code(event_type: str) -> str:
    """Return the stable SSE payload type code."""

    if event_type in STREAM_EVENT_TYPES:
        return STREAM_EVENT_TYPES[event_type].code  # type: ignore[index]
    return "SSE-900"


def storage_clear_scope_code(scope: str) -> str:
    """Return the stable storage-clear scope code."""

    if scope in STORAGE_CLEAR_SCOPES:
        return STORAGE_CLEAR_SCOPES[scope].code  # type: ignore[index]
    return "STG-900"


def api_error_body(code: str, message: str) -> dict[str, str]:
    """Build a JSON error payload with a stable response code."""

    return {"code": code, "error": message}


def api_error_code_for_message(message: str, http_status: int = HttpStatus.BAD_REQUEST) -> str:
    """Resolve a stable API error code from a validation message."""

    if message in _API_ERROR_MESSAGE_CODES:
        return _API_ERROR_MESSAGE_CODES[message]
    if http_status == HttpStatus.NOT_FOUND:
        return "API-4040"
    if message.startswith("Pexels"):
        return "API-4007"
    if "must be an integer" in message or "must be between" in message:
        return "API-4002"
    if "target" in message.lower() or "protocol" in message or "scope must be" in message:
        return "API-4006"
    if "speed test" in message.lower():
        return "API-4005"
    if "storage" in message.lower() or "unavailable" in message.lower():
        return "API-5030"
    return "API-4000"


def terminal_color_name(status: str) -> str:
    """Return the terminal color helper name for a monitor status."""

    if status in {"operational", "degraded", "down", "unknown"}:
        return status
    return "unknown"


def terminal_symbol(status: str) -> str:
    """Return the terminal glyph for a monitor status."""

    return monitor_status_definition(status).terminal_symbol
