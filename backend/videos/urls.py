# videos/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VideoViewSet,
    serve_stream_token,
    serve_master_playlist,
    serve_hls_playlist,
    serve_hls_segment,
    serve_aes_key,
    embed_video,
)

router = DefaultRouter()
router.register(r'', VideoViewSet, basename='video')

urlpatterns = [
    # ---------------- API ----------------
    path('', include(router.urls)),

    # ---------------- STREAM TOKEN (FIX) ----------------
    path(
        '<uuid:video_id>/stream-token/',
        serve_stream_token,
        name='serve_stream_token'
    ),

    # ---------------- EMBED ----------------
    path(
        'embed/<uuid:video_id>/',
        embed_video,
        name='video-embed'
    ),

    # ---------------- SECURE HLS ----------------
    path(
        'secure/hls/<uuid:video_id>/master.m3u8',
        serve_master_playlist,
        name='serve_master_playlist'
    ),
    path(
        'secure/hls/<uuid:video_id>/<str:quality>/playlist.m3u8',
        serve_hls_playlist,
        name='serve_hls_playlist'
    ),
    path(
        'secure/hls/<uuid:video_id>/<str:quality>/<str:segment_name>',
        serve_hls_segment,
        name='serve_hls_segment'
    ),

    # ---------------- AES KEY ----------------
    path(
        'secure/hls/<uuid:video_id>.key',
        serve_aes_key,
        name='serve_aes_key'
    ),
]
