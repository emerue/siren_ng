from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_organisation, name='org-register'),
    path('map/', views.organisations_map, name='org-map'),
    path('<uuid:pk>/respond/', views.organisation_respond, name='org-respond'),
    path('<uuid:pk>/', views.organisation_detail, name='org-detail'),
]
