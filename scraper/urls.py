from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scrape/', views.scrape_video, name='scrape_video'),
]
