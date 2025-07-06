"""Privacy-first telemetry collection for anonymous usage analytics."""

from .collector import TelemetryCollector
from .events import EventType, TelemetryEvent

__all__ = [
    'TelemetryCollector',
    'EventType',
    'TelemetryEvent'
]