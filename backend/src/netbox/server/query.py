"""HTTP query string and route parsing."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote


def parse_target_route(route: str) -> list[str] | None:
    """Parse `/api/targets/{id}` style routes."""

    prefix = "/api/targets/"
    if not route.startswith(prefix):
        return None

    remainder = route[len(prefix) :].strip("/")
    if not remainder:
        return None
    return [unquote(part) for part in remainder.split("/") if part]


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
