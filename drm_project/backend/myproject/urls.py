from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

# Views from videos app
from videos.views import (
    serve_aes_key,
    serve_hls_segment,
    serve_hls_playlist,
    serve_master_playlist,
    secure_file_response
)

@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('videos/', include('videos.urls')),
    path("csrf/", get_csrf),

    # ✅ Media routes
    path('media/videos/hls/<uuid:video_id>.key', serve_aes_key, name='serve_aes_key'),
    path('media/videos/hls/<uuid:video_id>/master.m3u8', serve_master_playlist, name='serve_master_playlist'),
    path('media/videos/hls/<uuid:video_id>/<str:quality>/playlist.m3u8', serve_hls_playlist, name='serve_hls_playlist'),
    path('media/videos/hls/<uuid:video_id>/<str:quality>/<str:segment_name>.ts', serve_hls_segment, name='serve_hls_segment'),

    # ✅ Secure direct path access
    path('secure/hls/<str:encoded_path>', secure_file_response, name='secure_file_response'),

    # ✅ Secure /secure/hls/<video_id>/... variant paths (REQUIRED by your frontend)
    path('secure/hls/<uuid:video_id>.key', serve_aes_key, name='secure_serve_aes_key'),
    path('secure/hls/<uuid:video_id>/master.m3u8', serve_master_playlist, name='secure_serve_master_playlist'),
    path('secure/hls/<uuid:video_id>/<str:quality>/playlist.m3u8', serve_hls_playlist, name='secure_serve_hls_playlist'),
    path('secure/hls/<uuid:video_id>/<str:quality>/<str:segment_name>.ts', serve_hls_segment, name='secure_serve_hls_segment'),
]

# ✅ Serve HLS & media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
