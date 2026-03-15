from django.shortcuts import render
from django.http import HttpResponse
from pathlib import Path
from django.conf import settings


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
