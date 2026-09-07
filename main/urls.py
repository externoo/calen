from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('day/<int:year>/<int:month>/<int:day>/', views.day, name='day'),
    path('commitment/<uuid:pk>/edit/', views.commitment_edit, name='commitment_edit'),
    path('commitment/<uuid:pk>/delete/', views.commitment_delete, name='commitment_delete'),
]
