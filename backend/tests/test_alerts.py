from netbox.alerts.dispatcher import should_trigger_alert
from netbox.alerts.models import normalize_smtp_payload, normalize_target_alert_payload


def test_normalize_target_alert_requires_email_to_when_email_enabled() -> None:
    try:
        normalize_target_alert_payload({"email": True})
    except ValueError as error:
        assert "emailTo" in str(error)
    else:
        raise AssertionError("expected validation error")


def test_normalize_smtp_payload_resend_defaults() -> None:
    payload = normalize_smtp_payload(
        {
            "provider": "resend",
            "fromEmail": "alerts@example.com",
            "password": "re_test",
        }
    )

    assert payload["host"] == "smtp.resend.com"
    assert payload["username"] == "resend"


def test_should_trigger_alert_respects_enabled_and_status() -> None:
    rules = {
        "enabled": True,
        "onDegraded": True,
        "onDown": False,
    }

    assert should_trigger_alert(rules, "degraded") is True
    assert should_trigger_alert(rules, "down") is False
    assert should_trigger_alert({**rules, "enabled": False}, "degraded") is False
