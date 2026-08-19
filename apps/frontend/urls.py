from django.urls import re_path
from . import views

# Catch-all: any path not matched earlier serves the React SPA.
#
# The negative lookahead matters: without it an unmatched /api/… path fell
# through to the SPA and returned index.html with HTTP 200. That silently
# turned "this endpoint does not exist" and "the backend is broken" into an
# apparently successful response, which masked a real production outage.
# API and admin paths now fall through to a normal 404 instead.
urlpatterns = [
    re_path(r'^(?!api/|admin/|health/|static/).*$', views.spa, name='spa'),
]
