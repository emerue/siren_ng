from django.urls import path
from . import views

urlpatterns = [
    path('', views.IncidentListView.as_view(), name='incident-list'),
    path('active/', views.active_incidents, name='incident-active'),
    path('<uuid:pk>/', views.incident_detail, name='incident-detail'),
    path('<uuid:pk>/track/', views.incident_track, name='incident-track'),
    path('<uuid:pk>/vouch/', views.incident_vouch, name='incident-vouch'),
    path('<uuid:pk>/dispatch/', views.incident_dispatch, name='incident-dispatch'),
    path('<uuid:pk>/resolve/', views.incident_resolve, name='incident-resolve'),
    path('<uuid:pk>/media/', views.upload_media, name='incident-media-upload'),
    path('<uuid:pk>/media/list/', views.list_media, name='incident-media-list'),
    path('<uuid:pk>/media/<int:media_pk>/', views.delete_media, name='incident-media-delete'),
]
