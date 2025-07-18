# videos/urls.py
from django.urls import path, include
from rest_framework import routers
from .views import VideoViewSet # You'll still need VideoViewSet here

router = routers.DefaultRouter()
router.register(r'', VideoViewSet)

urlpatterns = [
    path('', include(router.urls)) # This will handle /videos/ and /videos/<id>/
]