from django.urls import path
from . import views

urlpatterns = [
    path('web/', views.web_ingest, name='web-ingest'),
    path('whatsapp/', views.whatsapp_ingest, name='whatsapp-ingest'),
]
