"""Alert rules and SMTP settings persistence."""

from __future__ import annotations

from typing import Any

from netbox.alerts.models import DEFAULT_TARGET_ALERT, normalize_smtp_payload, normalize_target_alert_payload
from netbox.alerts.platform import platform_alert_defaults
from netbox.util.crypto import decrypt_secret, encrypt_secret


class AlertStoreMixin:
    """Target alert rules and encrypted SMTP provider settings."""

    path: Any

    def get_smtp_settings(self) -> dict[str, Any]:
        """Return stored SMTP settings including whether a password exists."""

        with self.lock:
            row = self.connection.execute(
                """
                SELECT provider, host, port, username, password_encrypted, from_email, from_name, use_tls, configured
                FROM smtp_settings
                WHERE id = 1
                """,
            ).fetchone()

        if row is None:
            return {
                "provider": "custom",
                "host": "",
                "port": 587,
                "username": "",
                "fromEmail": "",
                "fromName": "Netbox",
                "useTls": True,
                "configured": False,
                "hasPassword": False,
            }

        return {
            "provider": row["provider"],
            "host": row["host"],
            "port": int(row["port"]),
            "username": row["username"],
            "fromEmail": row["from_email"],
            "fromName": row["from_name"],
            "useTls": bool(row["use_tls"]),
            "configured": bool(row["configured"]),
            "hasPassword": bool(row["password_encrypted"]),
        }

    def get_smtp_password(self) -> str:
        """Decrypt the stored SMTP password, if configured."""

        with self.lock:
            row = self.connection.execute(
                "SELECT password_encrypted FROM smtp_settings WHERE id = 1",
            ).fetchone()
        if row is None or not row["password_encrypted"]:
            return ""
        return decrypt_secret(self.path, row["password_encrypted"])

    def update_smtp_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist SMTP settings, encrypting the password when provided."""

        normalized = normalize_smtp_payload(payload)
        current = self.get_smtp_settings()
        password = normalized.get("password")
        password_encrypted = ""
        if isinstance(password, str) and password:
            password_encrypted = encrypt_secret(self.path, password)
        elif current["hasPassword"]:
            with self.lock:
                row = self.connection.execute(
                    "SELECT password_encrypted FROM smtp_settings WHERE id = 1",
                ).fetchone()
            password_encrypted = row["password_encrypted"] if row else ""
        elif normalized["provider"] == "resend":
            raise ValueError("password is required for Resend SMTP")

        if not password_encrypted:
            raise ValueError("password is required")

        configured = bool(normalized["fromEmail"] and normalized["host"] and password_encrypted)
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO smtp_settings (
                  id, provider, host, port, username, password_encrypted,
                  from_email, from_name, use_tls, configured, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, unixepoch() * 1000)
                ON CONFLICT(id) DO UPDATE SET
                  provider = excluded.provider,
                  host = excluded.host,
                  port = excluded.port,
                  username = excluded.username,
                  password_encrypted = excluded.password_encrypted,
                  from_email = excluded.from_email,
                  from_name = excluded.from_name,
                  use_tls = excluded.use_tls,
                  configured = excluded.configured,
                  updated_at = excluded.updated_at
                """,
                (
                    normalized["provider"],
                    normalized["host"],
                    normalized["port"],
                    normalized["username"],
                    password_encrypted,
                    normalized["fromEmail"],
                    normalized["fromName"],
                    1 if normalized["useTls"] else 0,
                    1 if configured else 0,
                ),
            )
            self.connection.commit()

        return self.get_smtp_settings()

    def get_target_alert(self, target_id: str) -> dict[str, Any]:
        """Return alert rules for one target, falling back to defaults."""

        with self.lock:
            row = self.connection.execute(
                """
                SELECT enabled, notification, sound, email, email_to, on_degraded, on_down, cooldown_ms
                FROM target_alerts
                WHERE target_id = ?
                """,
                (target_id,),
            ).fetchone()

        if row is None:
            return platform_alert_defaults(self.get_platform_settings())

        return {
            "enabled": bool(row["enabled"]),
            "notification": bool(row["notification"]),
            "sound": bool(row["sound"]),
            "email": bool(row["email"]),
            "emailTo": row["email_to"] or "",
            "onDegraded": bool(row["on_degraded"]),
            "onDown": bool(row["on_down"]),
            "cooldownMs": int(row["cooldown_ms"]),
        }

    def update_target_alert(self, target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist alert rules for one target."""

        normalized = normalize_target_alert_payload(payload)
        smtp_configured = self.get_smtp_settings()["configured"]
        if normalized["email"] and not smtp_configured:
            raise ValueError("Configure SMTP before enabling email alerts")

        with self.lock:
            exists = self.connection.execute(
                "SELECT 1 FROM monitor_targets WHERE id = ?",
                (target_id,),
            ).fetchone()
            if exists is None:
                raise ValueError("target not found")

            self.connection.execute(
                """
                INSERT INTO target_alerts (
                  target_id, enabled, notification, sound, email, email_to,
                  on_degraded, on_down, cooldown_ms, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, unixepoch() * 1000)
                ON CONFLICT(target_id) DO UPDATE SET
                  enabled = excluded.enabled,
                  notification = excluded.notification,
                  sound = excluded.sound,
                  email = excluded.email,
                  email_to = excluded.email_to,
                  on_degraded = excluded.on_degraded,
                  on_down = excluded.on_down,
                  cooldown_ms = excluded.cooldown_ms,
                  updated_at = excluded.updated_at
                """,
                (
                    target_id,
                    1 if normalized["enabled"] else 0,
                    1 if normalized["notification"] else 0,
                    1 if normalized["sound"] else 0,
                    1 if normalized["email"] else 0,
                    normalized["emailTo"],
                    1 if normalized["onDegraded"] else 0,
                    1 if normalized["onDown"] else 0,
                    normalized["cooldownMs"],
                ),
            )
            self.connection.commit()

        return normalized

    def get_next_due_at(self, target_id: str, channel: str) -> int | None:
        """Return the persisted next-due timestamp for one alert channel."""

        with self.lock:
            row = self.connection.execute(
                """
                SELECT next_due_at
                FROM alert_dispatch_state
                WHERE target_id = ? AND channel = ?
                """,
                (target_id, channel),
            ).fetchone()
        if row is None:
            return None
        return int(row["next_due_at"])

    def mark_channel_sent(
        self,
        target_id: str,
        channel: str,
        *,
        sent_at: int,
        next_due_at: int,
    ) -> None:
        """Persist when one alert channel last fired and when it may fire again."""

        with self.lock:
            self.connection.execute(
                """
                INSERT INTO alert_dispatch_state (
                  target_id, channel, last_sent_at, next_due_at, updated_at
                )
                VALUES (?, ?, ?, ?, unixepoch() * 1000)
                ON CONFLICT(target_id, channel) DO UPDATE SET
                  last_sent_at = excluded.last_sent_at,
                  next_due_at = excluded.next_due_at,
                  updated_at = excluded.updated_at
                """,
                (target_id, channel, sent_at, next_due_at),
            )
            self.connection.commit()

    def clear_target(self, target_id: str) -> None:
        """Remove persisted alert schedules for one target."""

        with self.lock:
            self.connection.execute(
                "DELETE FROM alert_dispatch_state WHERE target_id = ?",
                (target_id,),
            )
            self.connection.commit()
