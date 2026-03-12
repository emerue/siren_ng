from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('report/', views.report, name='report'),
    path('track/', views.track_home, name='track-home'),
    path('track/<uuid:incident_id>/', views.track, name='track'),
    path('feed/', views.feed, name='feed'),
]
