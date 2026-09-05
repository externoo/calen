from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('day/<int:year>/<int:month>/<int:day>/', views.day, name='day'),
]
