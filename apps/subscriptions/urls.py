from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'lga', views.LGASubscriptionViewSet, basename='lga-subscription')

urlpatterns = [
    path('commute/', views.commute_create, name='commute-create'),
    path('my-impact/', views.my_impact, name='my-impact'),
    path('', include(router.urls)),
]
