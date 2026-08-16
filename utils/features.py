"""
v8 feature flags — single source of truth is settings.FEATURES.

Backend usage:
    from utils.features import feature_enabled
    if feature_enabled("commute_shield"):
        ...

Frontend reads the same state from GET /api/features/.
Flip a flag in the environment (Railway → Variables) and restart the service;
no code change or redeploy of logic is required.
"""
from django.conf import settings


def feature_enabled(name: str) -> bool:
    """True if the named feature is turned on. Unknown names are off."""
    return bool(settings.FEATURES.get(name, False))


def all_features() -> dict:
    """Full flag map {name: bool} — used by the /api/features/ endpoint."""
    return dict(settings.FEATURES)


def enabled_features() -> list:
    """Names of the currently-on features."""
    return [name for name, on in settings.FEATURES.items() if on]
