from django.urls import re_path
from . import views

# Catch-all: any path not matched by API/admin routes serves the React SPA
urlpatterns = [
    re_path(r'^.*$', views.spa, name='spa'),
]
