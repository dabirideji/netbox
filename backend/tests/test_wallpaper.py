import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from netbox.models import MonitorConfig, NetworkIdentity, Target
from netbox.server import StatusHandler, StatusServer
from netbox.state import MonitorState
from netbox.wallpaper import fetch_wallpaper


def config() -> MonitorConfig:
    return MonitorConfig(
        duration_ms=10_000,
        interval_ms=1_000,
        timeout_ms=900,
        port=0,
        host="127.0.0.1",
        latency_warn_ms=100,
        failures_to_degrade=1,
        failures_to_down=2,
        high_latency_to_degrade=1,
        recent_window=5,
        history_points=5,
        retention_points=10,
        no_clear=True,
        wifi_name="",
        db_path=":memory:",
    )


def test_fetch_wallpaper_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    with pytest.raises(ValueError, match="PEXELS_API_KEY is not configured"):
        fetch_wallpaper()


def test_fetch_wallpaper_returns_image_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    payload = {
        "photos": [
            {
                "photographer": "Jane Doe",
                "url": "https://www.pexels.com/photo/example/",
                "src": {
                    "large2x": "https://images.pexels.com/photos/example-large2x.jpeg",
                    "medium": "https://images.pexels.com/photos/example-medium.jpeg",
                },
            }
        ]
    }

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

    captured: dict[str, urllib.request.Request] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float = 0) -> FakeResponse:
        captured["request"] = request
        return FakeResponse()

    with patch("netbox.wallpaper.urllib.request.urlopen", side_effect=fake_urlopen):
        result = fetch_wallpaper()

    request_url = captured["request"].full_url
    assert "/v1/search?" in request_url
    assert "orientation=landscape" in request_url
    assert "query=" in request_url
    assert result == {
        "url": "https://images.pexels.com/photos/example-large2x.jpeg",
        "photographer": "Jane Doe",
        "photoUrl": "https://www.pexels.com/photo/example/",
    }


def test_wallpaper_api_returns_image_payload(tmp_path: Path) -> None:
    wallpaper = {
        "url": "https://images.pexels.com/photos/example.jpeg",
        "photographer": "Jane Doe",
        "photoUrl": "https://www.pexels.com/photo/example/",
    }
    (tmp_path / "index.html").write_text("<div id='app'></div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with (
            patch("netbox.server.fetch_wallpaper", return_value=wallpaper),
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/wallpaper", timeout=3) as response,
        ):
            body = json.load(response)

        assert body == wallpaper
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()


def test_wallpaper_api_returns_error_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    (tmp_path / "index.html").write_text("<div id='app'></div>")
    target = Target("gateway", "127.0.0.1", "Loopback", "gateway")
    state = MonitorState(config(), [target], NetworkIdentity("Test", "Test", "en0", "Wi-Fi"), 0)
    server = StatusServer(("127.0.0.1", 0), StatusHandler, state, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/wallpaper", timeout=3)

        assert error.value.code == 400
        payload = json.loads(error.value.read().decode())
        assert payload["error"] == "PEXELS_API_KEY is not configured"
    finally:
        state.stopping.set()
        server.shutdown()
        server.server_close()
