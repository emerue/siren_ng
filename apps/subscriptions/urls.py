from django.urls import path
from . import views

urlpatterns = [
    path('', views.subscription_list_create, name='subscription-list-create'),
    path('<uuid:pk>/', views.subscription_detail, name='subscription-detail'),
    path('commute/', views.commute_create, name='commute-create'),
    path('my-impact/', views.my_impact, name='my-impact'),
]
