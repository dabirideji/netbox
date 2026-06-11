"""Composed SQLite store for monitor persistence."""

from __future__ import annotations

from netbox.storage.alerts import AlertStoreMixin
from netbox.storage.base import StoreBase
from netbox.storage.events import EventStoreMixin
from netbox.storage.history import HistoryStoreMixin
from netbox.storage.maintenance import MaintenanceStoreMixin
from netbox.storage.platform import PlatformStoreMixin
from netbox.storage.settings_store import StorageSettingsStoreMixin
from netbox.storage.preferences import PreferenceStoreMixin
from netbox.storage.samples import SampleStoreMixin
from netbox.storage.speed_tests import SpeedTestStoreMixin
from netbox.storage.targets import TargetStoreMixin


class StatusStore(
    AlertStoreMixin,
    PlatformStoreMixin,
    StorageSettingsStoreMixin,
    MaintenanceStoreMixin,
    PreferenceStoreMixin,
    SpeedTestStoreMixin,
    EventStoreMixin,
    HistoryStoreMixin,
    SampleStoreMixin,
    TargetStoreMixin,
    StoreBase,
):
    """Thread-safe SQLite gateway for monitor history data."""
