"""
Coordinator coverage hours.

Siren only broadcasts when a human confirms, so outside the hours a coordinator
is actually on duty we must tell a reporter the truth: the report is queued, not
being looked at this second. This module decides which it is.

Nothing here may raise. It is called from inside the Twilio webhook path, and a
malformed environment variable must never cost us an inbound emergency report.
"""
import logging
from datetime import time

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_START = time(7, 0)
DEFAULT_END = time(21, 0)


def _parse(value, fallback: time) -> time:
    """Parse "HH:MM" into a time, falling back loudly rather than raising."""
    try:
        hour, _, minute = str(value).strip().partition(":")
        parsed = time(int(hour), int(minute or 0))
    except (ValueError, TypeError):
        logger.warning(
            "coverage: could not parse %r as HH:MM; using %s", value, fallback
        )
        return fallback
    return parsed


def coverage_window():
    """(start, end) as time objects, in Africa/Lagos (the project TIME_ZONE)."""
    return (
        _parse(getattr(settings, "COORDINATOR_COVERAGE_START", None), DEFAULT_START),
        _parse(getattr(settings, "COORDINATOR_COVERAGE_END", None), DEFAULT_END),
    )


def is_within_coverage(now=None) -> bool:
    """True if a coordinator is expected to be on duty right now."""
    try:
        current = (now or timezone.localtime()).time()
        start, end = coverage_window()
        if start == end:
            return True  # a zero-width window is meaningless; treat as always-on
        if start < end:
            return start <= current < end
        # Wrap-around window, e.g. 21:00 -> 07:00.
        return current >= start or current < end
    except Exception:
        # Fail open: assume covered, so the reporter gets the normal
        # acknowledgment rather than an outage-flavoured one.
        logger.exception("coverage: check failed; assuming within coverage")
        return True
