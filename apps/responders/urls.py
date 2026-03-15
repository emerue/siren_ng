from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_responder, name='responder-register'),
    path('availability/', views.toggle_availability, name='responder-availability'),
    path('dispatch/<uuid:pk>/accept/', views.dispatch_accept, name='dispatch-accept'),
    path('dispatch/<uuid:pk>/decline/', views.dispatch_decline, name='dispatch-decline'),
    path('dispatch/<uuid:pk>/onscene/', views.dispatch_onscene, name='dispatch-onscene'),
    path('dispatch/<uuid:pk>/complete/', views.dispatch_complete, name='dispatch-complete'),
]
