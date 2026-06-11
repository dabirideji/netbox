from __future__ import annotations

from unittest.mock import patch

from netbox.alerts.dispatcher import dispatch_ongoing_alerts, dispatch_target_alerts
from netbox.alerts.schedule import EMAIL_REMINDER_MS, SOUND_REMINDER_MS, channel_reminder_ms


class MemoryDispatchStore:
    """In-memory stand-in for persisted alert dispatch schedules."""

    def __init__(self) -> None:
        self.next_due: dict[tuple[str, str], int] = {}

    def get_next_due_at(self, target_id: str, channel: str) -> int | None:
        return self.next_due.get((target_id, channel))

    def mark_channel_sent(
        self,
        target_id: str,
        channel: str,
        *,
        sent_at: int,
        next_due_at: int,
    ) -> None:
        self.next_due[(target_id, channel)] = next_due_at

    def clear_target(self, target_id: str) -> None:
        for key in [item for item in self.next_due if item[0] == target_id]:
            del self.next_due[key]


def default_rules(**overrides: object) -> dict[str, object]:
    rules = {
        "enabled": True,
        "notification": False,
        "sound": True,
        "email": True,
        "emailTo": "ops@example.com",
        "onDegraded": True,
        "onDown": True,
        "cooldownMs": 300_000,
    }
    rules.update(overrides)
    return rules


def test_channel_reminder_intervals() -> None:
    rules = default_rules()

    assert channel_reminder_ms("sound", rules) == SOUND_REMINDER_MS
    assert channel_reminder_ms("email", rules) == EMAIL_REMINDER_MS
    assert channel_reminder_ms("notification", rules) == 300_000


def test_transition_alert_fires_immediately_and_sets_timer() -> None:
    broadcasts: list[dict[str, object]] = []
    dispatch_store = MemoryDispatchStore()
    event = {
        "at": 1_000,
        "targetId": "api-1",
        "targetLabel": "API",
        "from": "operational",
        "to": "down",
        "message": "API changed from operational to down",
    }

    with patch("netbox.alerts.dispatcher.now_ms", return_value=1_000):
        dispatch_target_alerts(
            [event],
            get_rules=lambda _target_id: default_rules(),
            smtp_settings={"configured": True},
            smtp_password="secret",
            dispatch_store=dispatch_store,
            broadcast=broadcasts.append,
        )

    assert len(broadcasts) == 1
    assert broadcasts[0]["type"] == "alert"
    assert dispatch_store.next_due[("api-1", "sound")] == 1_000 + SOUND_REMINDER_MS
    assert dispatch_store.next_due[("api-1", "email")] == 1_000 + EMAIL_REMINDER_MS


def test_ongoing_sound_repeats_after_interval() -> None:
    broadcasts: list[dict[str, object]] = []
    dispatch_store = MemoryDispatchStore()
    dispatch_store.next_due[("api-1", "sound")] = 1_000 + SOUND_REMINDER_MS
    summary = {
        "targets": [
            {
                "id": "api-1",
                "label": "API",
                "currentStatus": "down",
            }
        ]
    }

    with patch("netbox.alerts.dispatcher.now_ms", return_value=1_000 + SOUND_REMINDER_MS - 1):
        dispatch_ongoing_alerts(
            summary,
            get_rules=lambda _target_id: default_rules(),
            smtp_settings=None,
            smtp_password="",
            dispatch_store=dispatch_store,
            broadcast=broadcasts.append,
        )
    assert broadcasts == []

    with patch("netbox.alerts.dispatcher.now_ms", return_value=1_000 + SOUND_REMINDER_MS):
        dispatch_ongoing_alerts(
            summary,
            get_rules=lambda _target_id: default_rules(),
            smtp_settings=None,
            smtp_password="",
            dispatch_store=dispatch_store,
            broadcast=broadcasts.append,
        )

    assert len(broadcasts) == 1
    alert = broadcasts[0]["alert"]
    assert alert["channel"] == "sound"
    assert alert["reminder"] is True


def test_ongoing_email_waits_fifteen_minutes() -> None:
    dispatch_store = MemoryDispatchStore()
    dispatch_store.next_due[("api-1", "email")] = 1_000 + EMAIL_REMINDER_MS
    summary = {
        "targets": [
            {
                "id": "api-1",
                "label": "API",
                "currentStatus": "down",
            }
        ]
    }

    with patch("netbox.alerts.dispatcher.threading.Thread") as thread:
        with patch("netbox.alerts.dispatcher.now_ms", return_value=1_000 + EMAIL_REMINDER_MS - 1):
            dispatch_ongoing_alerts(
                summary,
                get_rules=lambda _target_id: default_rules(),
                smtp_settings={"configured": True},
                smtp_password="secret",
                dispatch_store=dispatch_store,
                broadcast=lambda _payload: None,
            )
        thread.assert_not_called()

        with patch("netbox.alerts.dispatcher.now_ms", return_value=1_000 + EMAIL_REMINDER_MS):
            dispatch_ongoing_alerts(
                summary,
                get_rules=lambda _target_id: default_rules(),
                smtp_settings={"configured": True},
                smtp_password="secret",
                dispatch_store=dispatch_store,
                broadcast=lambda _payload: None,
            )
        thread.assert_called_once()


def test_recovery_clears_repeat_timers() -> None:
    dispatch_store = MemoryDispatchStore()
    dispatch_store.next_due[("api-1", "sound")] = 2_000
    dispatch_store.next_due[("api-1", "email")] = 2_000

    dispatch_store.clear_target("api-1")

    assert dispatch_store.next_due == {}


def test_recovery_event_clears_timers_without_alert() -> None:
    broadcasts: list[dict[str, object]] = []
    dispatch_store = MemoryDispatchStore()
    dispatch_store.next_due[("api-1", "sound")] = 2_000
    dispatch_store.next_due[("api-1", "email")] = 2_000

    dispatch_target_alerts(
        [
            {
                "at": 2_000,
                "targetId": "api-1",
                "targetLabel": "API",
                "from": "down",
                "to": "operational",
                "message": "API recovered",
            }
        ],
        get_rules=lambda _target_id: default_rules(),
        smtp_settings=None,
        smtp_password="",
        dispatch_store=dispatch_store,
        broadcast=broadcasts.append,
    )

    assert broadcasts == []
    assert dispatch_store.next_due == {}
