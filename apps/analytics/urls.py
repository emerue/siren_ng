from django.urls import path
from . import views

urlpatterns = [
    path('summary/', views.analytics_summary, name='analytics-summary'),
    path('zones/', views.analytics_zones, name='analytics-zones'),
    path('trends/', views.analytics_trends, name='analytics-trends'),
    path('donations/', views.analytics_donations, name='analytics-donations'),
    path('subscribers/', views.analytics_subscribers, name='analytics-subscribers'),
]
