"""HTTP method route dispatch for the monitor API."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import ParseResult

from netbox.core.responses import HttpStatus
from netbox.server.query import parse_query, parse_target_route
from netbox.server.wallpaper import fetch_wallpaper
from netbox.util.macos import detect_location_client

if TYPE_CHECKING:
    from netbox.server.handler import StatusHandler


def dispatch_get(handler: StatusHandler, parsed_url: ParseResult) -> bool:
    """Handle one GET request when it matches a known API route."""

    route = parsed_url.path
    state = handler.app_server.state

    if route == "/api/status":
        handler.write_json(state.snapshot())
        return True

    if route == "/api/history":
        query = parse_query(parsed_url.query)
        handler.write_json(state.history(query["points"], query["from"], query["to"]))
        return True

    if route == "/api/targets/history":
        query = parse_query(parsed_url.query)
        handler.write_json(state.target_history(query["points"], query["from"], query["to"]))
        return True

    if route == "/api/targets":
        handler.write_json(state.list_targets())
        return True

    target_route = parse_target_route(route)
    if target_route and len(target_route) == 1:
        handler.write_json(state.get_target(target_route[0]))
        return True

    if target_route and len(target_route) == 2 and target_route[1] == "results":
        query = parse_query(parsed_url.query)
        handler.write_json(
            state.target_results(
                target_route[0],
                query["limit"],
                query["from"],
                query["to"],
                query["offset"],
            )
        )
        return True

    if target_route and len(target_route) == 2 and target_route[1] == "alert":
        handler.write_json(state.target_alert(target_route[0]))
        return True

    if route == "/api/incidents":
        query = parse_query(parsed_url.query)
        handler.write_json(
            state.incidents(query["limit"], query["from"], query["to"], query["offset"]),
        )
        return True

    if route == "/api/events":
        query = parse_query(parsed_url.query)
        handler.write_json(
            state.persisted_events(query["limit"], query["from"], query["to"], query["offset"]),
        )
        return True

    if route == "/api/speed-tests":
        query = parse_query(parsed_url.query)
        handler.write_json(
            state.speed_tests(query["limit"], query["from"], query["to"], query["offset"]),
        )
        return True

    if route == "/api/network/location-client":
        handler.write_json({"client": detect_location_client()})
        return True

    if route == "/api/network/interfaces":
        handler.write_json(state.list_network_interfaces())
        return True

    if route == "/api/preferences":
        handler.write_json(state.preferences())
        return True

    if route == "/api/alerts/smtp":
        handler.write_json(state.smtp_settings())
        return True

    if route == "/api/settings/platform":
        handler.write_json(state.platform_settings())
        return True

    if route == "/api/storage":
        handler.write_json(state.storage_stats())
        return True

    if route == "/api/storage/settings":
        handler.write_json(state.storage_settings())
        return True

    if route == "/api/wallpaper":
        handler.write_json(fetch_wallpaper())
        return True

    return False


def dispatch_post(handler: StatusHandler, route: str) -> bool:
    """Handle one POST request when it matches a known API route."""

    state = handler.app_server.state

    if route == "/api/targets":
        handler.write_json(state.create_target(handler.read_json_body()), status=HttpStatus.CREATED)
        return True

    if route == "/api/targets/preview-check":
        handler.write_json(state.preview_target_check(handler.read_json_body()), status=HttpStatus.OK)
        return True

    target_route = parse_target_route(route)
    if target_route and len(target_route) == 2 and target_route[1] == "check-now":
        handler.write_json(state.check_now(target_route[0]), status=HttpStatus.ACCEPTED)
        return True

    if route == "/api/speed-tests":
        handler.write_json(state.record_speed_test(handler.read_json_body()), status=HttpStatus.CREATED)
        return True

    if route == "/api/network/refresh":
        wifi_name = None
        interface = None
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        if content_length > 0:
            payload = handler.read_json_body()
            raw_wifi_name = payload.get("wifiName")
            if raw_wifi_name is not None:
                if not isinstance(raw_wifi_name, str):
                    raise ValueError("wifiName must be a string")
                wifi_name = raw_wifi_name
            raw_interface = payload.get("interface")
            if raw_interface is not None:
                if not isinstance(raw_interface, str):
                    raise ValueError("interface must be a string")
                interface = raw_interface
        handler.write_json(
            state.refresh_network_identity(wifi_name, interface),
            status=HttpStatus.OK,
        )
        return True

    if route == "/api/storage/clear":
        payload = handler.read_json_body()
        scope = payload.get("scope")
        if not isinstance(scope, str):
            raise ValueError("scope is required")
        handler.write_json(state.clear_storage(scope))
        return True

    if route == "/api/alerts/smtp/test":
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        payload = handler.read_json_body() if content_length > 0 else {}
        handler.write_json(state.test_smtp_settings(payload), status=HttpStatus.OK)
        return True

    return False


def dispatch_patch(handler: StatusHandler, route: str) -> bool:
    """Handle one PATCH request when it matches a known API route."""

    state = handler.app_server.state
    target_route = parse_target_route(route)

    if route == "/api/targets/order":
        handler.write_json(state.reorder_targets(handler.read_json_body()))
        return True

    if target_route and len(target_route) == 1:
        handler.write_json(state.update_target(target_route[0], handler.read_json_body()))
        return True

    if route == "/api/preferences":
        handler.write_json(state.update_preferences(handler.read_json_body()))
        return True

    if route == "/api/alerts/smtp":
        handler.write_json(state.update_smtp_settings(handler.read_json_body()))
        return True

    if route == "/api/settings/platform":
        handler.write_json(state.update_platform_settings(handler.read_json_body()))
        return True

    if route == "/api/storage/settings":
        handler.write_json(state.update_storage_settings(handler.read_json_body()), status=HttpStatus.OK)
        return True

    if target_route and len(target_route) == 2 and target_route[1] == "alert":
        handler.write_json(state.update_target_alert(target_route[0], handler.read_json_body()))
        return True

    if target_route and len(target_route) == 2 and target_route[1] == "favorite":
        handler.write_json(state.set_target_favorite(target_route[0], handler.read_json_body()))
        return True

    return False


def dispatch_delete(handler: StatusHandler, route: str) -> bool:
    """Handle one DELETE request when it matches a known API route."""

    target_route = parse_target_route(route)
    if target_route and len(target_route) == 1:
        handler.write_json(handler.app_server.state.delete_target(target_route[0]))
        return True

    return False
