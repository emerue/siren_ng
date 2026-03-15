from django.urls import path
from . import views

urlpatterns = [
    path('', views.resource_list_create, name='resource-list-create'),
    path('<uuid:pk>/claim/', views.resource_claim, name='resource-claim'),
    path('<uuid:pk>/confirm/', views.resource_confirm, name='resource-confirm'),
    path('donate/', views.donate_initiate, name='donate-initiate'),
    path('donate/verify/', views.donate_verify, name='donate-verify'),
    path('donations/', views.donate_summary, name='donate-summary'),
]
