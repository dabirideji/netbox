"""Speed-test policy helpers."""

from netbox.speed import speed_policy


def test_speed_policy_allows_immediate_rerun_when_interval_disabled() -> None:
    now_ms = 1_000_000
    latest = {"testedAt": now_ms - 5_000}
    config = {"enabled": True, "minIntervalMinutes": 0, "dailyRunLimit": 0}

    policy = speed_policy(config, latest, runs_last_day=3, now_ms=now_ms)

    assert policy["canRun"] is True
    assert policy["nextRunAt"] is None


def test_speed_policy_blocks_until_interval_elapses() -> None:
    now_ms = 1_000_000
    latest = {"testedAt": now_ms - 60_000}
    config = {"enabled": True, "minIntervalMinutes": 15, "dailyRunLimit": 0}

    policy = speed_policy(config, latest, runs_last_day=1, now_ms=now_ms)

    assert policy["canRun"] is False
    assert policy["nextRunAt"] == latest["testedAt"] + 15 * 60 * 1000
