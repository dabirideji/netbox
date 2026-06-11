"""Server-side alert scheduling helpers."""

from __future__ import annotations

from typing import Any, Protocol

SOUND_REMINDER_MS = 60_000
EMAIL_REMINDER_MS = 900_000
ALERT_TICK_INTERVAL_MS = 10_000


class AlertDispatchStore(Protocol):
    """Persistence for per-target alert channel schedules."""

    def get_next_due_at(self, target_id: str, channel: str) -> int | None:
        """Return the next wall-clock time one channel may fire again."""

    def mark_channel_sent(
        self,
        target_id: str,
        channel: str,
        *,
        sent_at: int,
        next_due_at: int,
    ) -> None:
        """Persist the last send time and the next allowed send time."""

    def clear_target(self, target_id: str) -> None:
        """Drop all channel schedules after a target recovers."""


def channel_reminder_ms(channel: str, rules: dict[str, Any]) -> int:
    """Return the repeat interval for one alert channel."""

    if channel == "email":
        return EMAIL_REMINDER_MS
    if channel == "sound":
        return SOUND_REMINDER_MS
    return int(rules.get("cooldownMs") or 300_000)


def channel_is_due(
    dispatch_store: AlertDispatchStore,
    target_id: str,
    channel: str,
    now: int,
    *,
    enforce_interval: bool,
) -> bool:
    """Return whether one alert channel is allowed to fire at `now`."""

    if not enforce_interval:
        return True

    next_due_at = dispatch_store.get_next_due_at(target_id, channel)
    if next_due_at is None:
        return True
    return now >= next_due_at


def mark_channel_sent(
    dispatch_store: AlertDispatchStore,
    target_id: str,
    channel: str,
    *,
    now: int,
    rules: dict[str, Any],
) -> None:
    """Record one successful alert dispatch and schedule the next reminder."""

    interval = channel_reminder_ms(channel, rules)
    dispatch_store.mark_channel_sent(
        target_id,
        channel,
        sent_at=now,
        next_due_at=now + interval,
    )
