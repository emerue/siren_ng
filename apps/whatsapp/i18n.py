"""
Per-user language preference for outbound WhatsApp copy (v8 §7 NFR:
English + Pidgin at launch).

Model: default English; the sender texts PIDGIN / ENGLISH to choose. The choice
is stored durably on WhatsAppProfile (hash-keyed). First contact is answered
bilingually so the sender learns they can switch.
"""
import logging

logger = logging.getLogger(__name__)

EN = 'en'
PCM = 'pcm'


def get_language(from_number: str) -> str:
    """Stored language for this number, or 'en' by default."""
    from apps.whatsapp.models import WhatsAppProfile
    try:
        p = WhatsAppProfile.objects.filter(
            number_hash=WhatsAppProfile.hash_number(from_number)
        ).only('language').first()
        return p.language if p else EN
    except Exception as exc:  # never let a preference lookup block delivery
        logger.warning("get_language failed for hashed number: %s", exc)
        return EN


def has_language_preference(from_number: str) -> bool:
    from apps.whatsapp.models import WhatsAppProfile
    try:
        return WhatsAppProfile.objects.filter(
            number_hash=WhatsAppProfile.hash_number(from_number)
        ).exists()
    except Exception:
        return False


def set_language(from_number: str, language: str):
    from apps.whatsapp.models import WhatsAppProfile
    if language not in (EN, PCM):
        language = EN
    WhatsAppProfile.objects.update_or_create(
        number_hash=WhatsAppProfile.hash_number(from_number),
        defaults={'language': language},
    )
