from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from pathlib import Path
from django.conf import settings


def site_config(request):
    """Public, non-secret runtime configuration for the web client.

    GET /api/config/ -> {"whatsapp_number": "+234...", "site_url": "..."}

    The WhatsApp number lives here rather than in a VITE_ build variable
    because Vite inlines env vars at BUILD time: the Docker frontend stage
    never sees Railway's service variables, so the placeholder fallback got
    compiled into the bundle. Serving it at runtime means changing the number
    is an env var + restart, with no rebuild.

    Only values that are already public may be added here.
    """
    number = str(getattr(settings, 'TWILIO_WHATSAPP_NUMBER', '') or '')
    # Stored Twilio-side as "whatsapp:+234…"; the client wants a bare number.
    number = number.replace('whatsapp:', '').strip()
    return JsonResponse({
        'whatsapp_number': number,
        'site_url': getattr(settings, 'SITE_URL', ''),
    })


def feature_flags(request):
    """Public read-only feature-flag state for the frontend to gate UI.

    GET /api/features/ -> {"features": {"donations": false, ...}}
    Lets the web UI show/hide OUT/HIDDEN features based on env flags without a
    rebuild. Toggle in Railway → Variables, restart, and the UI follows.
    """
    from utils.features import all_features
    return JsonResponse({"features": all_features()})


def spa(request, *args, **kwargs):
    """Serve the React SPA for all non-API routes."""
    index = Path(settings.BASE_DIR) / 'frontend' / 'dist' / 'index.html'
    if index.exists():
        return HttpResponse(index.read_text(encoding='utf-8'))
    # Fallback for dev (Vite running separately)
    return HttpResponse(
        '<p>Frontend not built. Run <code>npm run build</code> inside <code>frontend/</code>.</p>',
        status=200,
    )
