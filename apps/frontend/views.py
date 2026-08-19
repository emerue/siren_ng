from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from pathlib import Path
from django.conf import settings


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
