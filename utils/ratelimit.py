"""
Identity normalisation, hashing and rate limiting.

BRD §7 security invariants:
  - rate limiting is keyed on hashed phone identity, never on IP
  - reporter_hash (SHA-256) is used for all identity lookups

Two defects this module fixes:
  1. The previous limiter hashed the raw `From` string, so trivial reformatting
     ("+2348012345678" vs "2348012345678" vs "08012345678" vs added whitespace)
     produced different keys and reset the quota. Identity is now normalised to
     E.164 before hashing.
  2. The previous limiter did get-then-set, which is not atomic: concurrent
     requests all read the same count and each wrote count+1, so a burst
     sailed past the limit. It now uses an atomic add/incr.
"""
import hashlib
import re

from django.core.cache import cache

NG_COUNTRY_CODE = "234"


def normalize_phone(raw: str) -> str:
    """Reduce a phone identity to canonical E.164 digits.

    Handles the Twilio `whatsapp:` prefix, spaces, dashes, brackets, a leading
    `+`, and the Nigerian local `0…` form.
    """
    if not raw:
        return ""
    s = str(raw).strip().lower()
    if s.startswith("whatsapp:"):
        s = s[len("whatsapp:"):]
    digits = re.sub(r"\D", "", s)
    if not digits:
        return ""
    # Local Nigerian format: 0803… → 234803…
    if digits.startswith("0"):
        digits = NG_COUNTRY_CODE + digits.lstrip("0")
    # Some senders omit the country code entirely (10 significant digits).
    elif len(digits) == 10:
        digits = NG_COUNTRY_CODE + digits
    return digits


def phone_hash(raw: str) -> str:
    """SHA-256 of the normalised identity. Never store/log the raw number."""
    return hashlib.sha256(normalize_phone(raw).encode()).hexdigest()


def hit_rate_limit(identity: str, *, rate: int = 10, window: int = 60,
                   scope: str = "wa") -> bool:
    """Atomically record a hit. Returns True if the caller is OVER the limit.

    Fails open on cache backend errors: an unavailable cache must never block
    an emergency report.
    """
    key = f"rl:{scope}:{phone_hash(identity)[:32]}"
    try:
        # add() is atomic and only succeeds on the first call in the window,
        # which is what establishes the TTL.
        if cache.add(key, 1, window):
            return False
        try:
            count = cache.incr(key)
        except ValueError:
            # Key expired between add() and incr(); start a fresh window.
            cache.set(key, 1, window)
            return False
        return count > rate
    except Exception:
        return False


def masked(raw: str) -> str:
    """Log-safe identity: a short hash prefix, never digits of the number."""
    h = phone_hash(raw)
    return f"phone#{h[:10]}" if raw else "phone#none"
