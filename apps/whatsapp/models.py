import hashlib
from django.db import models


class WhatsAppProfile(models.Model):
    """Durable per-sender preferences, keyed by the SHA-256 hash of the number
    (never the raw number — v8 §7 security invariant). Currently holds the
    language preference for outbound copy (English / Nigerian Pidgin)."""

    LANG_EN = 'en'
    LANG_PCM = 'pcm'
    LANG_CHOICES = [
        (LANG_EN, 'English'),
        (LANG_PCM, 'Nigerian Pidgin'),
    ]

    number_hash = models.CharField(max_length=64, unique=True, db_index=True)
    language = models.CharField(max_length=5, choices=LANG_CHOICES, default=LANG_EN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"WhatsAppProfile({self.number_hash[:8]}…, {self.language})"

    @staticmethod
    def hash_number(number: str) -> str:
        return hashlib.sha256(str(number).encode()).hexdigest()
