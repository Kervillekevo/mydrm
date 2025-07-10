# backend/videos/urls.py

from django.urls import path, include
from.views import serve_aes_key
from rest_framework import routers
from.views import VideoViewSet

router = routers.DefaultRouter()
router.register(r'videos', VideoViewSet)

urlpatterns = [
    # Nothing for now.
      path('key/<uuid:video_id>.key', serve_aes_key, name='serve_aes_key'),
      path('', include(router.urls))
]
