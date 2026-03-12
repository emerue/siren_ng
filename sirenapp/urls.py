from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ingest/', include('apps.whatsapp.urls')),
    path('api/incidents/', include('apps.incidents.urls')),
    path('api/responders/', include('apps.responders.urls')),
    path('api/organisations/', include('apps.organisations.urls')),
    path('api/resources/', include('apps.resources.urls')),
    path('api/subscriptions/', include('apps.subscriptions.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('apps.frontend.urls')),
]
