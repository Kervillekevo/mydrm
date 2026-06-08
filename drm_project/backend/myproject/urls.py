from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from videos.views import (
    serve_aes_key,
    serve_hls_segment,          # legacy — now returns 410
    serve_hls_segment_alias,    # ✅ NEW — single-use alias endpoint
    serve_hls_playlist,
    serve_master_playlist,
    secure_file_response,
    embed_video,
)


@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('videos/', include('videos.urls')),
    path('csrf/', get_csrf),

    # ------------------------------------------------------------------
    # ✅ NEW — VDH-defeating stream endpoints
    #    No .m3u8 extension, no .ts extension, generic-looking paths
    # ------------------------------------------------------------------

    # Master playlist  (was: /secure/hls/<id>/master.m3u8)
    path(
        'api/stream/<uuid:video_id>/master',
        serve_master_playlist,
        name='serve_master_playlist',
    ),

    # Quality playlist  (was: /secure/hls/<id>/<quality>/playlist.m3u8)
    path(
        'api/stream/<uuid:video_id>/<str:quality>/index',
        serve_hls_playlist,
        name='serve_hls_playlist',
    ),

    # ✅ Single-use segment alias  (NEW — VDH captures dead URLs)
    path(
        'api/stream/chunk/<str:alias>.bin',
        serve_hls_segment_alias,
        name='serve_hls_segment_alias',
    ),

    # AES key  (path changed — no longer publicly guessable)
    path(
        'api/stream/<uuid:video_id>/key',
        serve_aes_key,
        name='serve_aes_key',
    ),

    # ------------------------------------------------------------------
    # 🔒 Legacy routes — kept so bookmarks / old embeds don't hard-crash
    #    They now return 410 Gone
    # ------------------------------------------------------------------
    path(
        'media/videos/hls/<uuid:video_id>/master.m3u8',
        serve_master_playlist,
        name='legacy_master_playlist',
    ),
    path(
        'media/videos/hls/<uuid:video_id>/<str:quality>/playlist.m3u8',
        serve_hls_playlist,
        name='legacy_hls_playlist',
    ),
    path(
        'media/videos/hls/<uuid:video_id>/<str:quality>/<str:segment_name>.ts',
        serve_hls_segment,          # returns 410
        name='legacy_hls_segment',
    ),
    path(
        'media/videos/hls/<uuid:video_id>.key',
        serve_aes_key,
        name='legacy_aes_key',
    ),

    # Secure base64 path (unchanged)
    path(
        'secure/hls/<str:encoded_path>',
        secure_file_response,
        name='secure_file_response',
    ),

    # Secure variant paths (kept for backwards compat)
    path(
        'secure/hls/<uuid:video_id>/master.m3u8',
        serve_master_playlist,
        name='secure_serve_master_playlist',
    ),
    path(
        'secure/hls/<uuid:video_id>/<str:quality>/playlist.m3u8',
        serve_hls_playlist,
        name='secure_serve_hls_playlist',
    ),
    path(
        'secure/hls/<uuid:video_id>/<str:quality>/<str:segment_name>.ts',
        serve_hls_segment,          # returns 410
        name='secure_serve_hls_segment',
    ),
    path(
        'secure/hls/<uuid:video_id>.key',
        serve_aes_key,
        name='secure_serve_aes_key',
    ),

    # Embed
    path('embed/<uuid:video_id>/', embed_video, name='video-embed'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)