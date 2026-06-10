from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VideoViewSet,
    serve_stream_token,
    serve_master_playlist,
    serve_hls_playlist,
    serve_hls_segment,
    serve_hls_segment_alias,
    serve_aes_key,
    embed_video,
)

router = DefaultRouter()
router.register(r'', VideoViewSet, basename='video')

urlpatterns = [
    path('', include(router.urls)),

    path('<uuid:video_id>/stream-token/', serve_stream_token, name='serve_stream_token'),

    path('embed/<uuid:video_id>/', embed_video, name='video-embed'),

    path('media/<uuid:video_id>/manifest', serve_master_playlist, name='serve_master_playlist'),

    path('media/<uuid:video_id>/<str:quality>/data', serve_hls_playlist, name='serve_hls_playlist'),

    path('media/chunk/<str:alias>.bin', serve_hls_segment_alias, name='serve_hls_segment_alias'),

    path('media/<uuid:video_id>/key', serve_aes_key, name='serve_aes_key'),

    path('secure/hls/<uuid:video_id>/<str:quality>/<str:segment_name>', serve_hls_segment, name='serve_hls_segment'),
]