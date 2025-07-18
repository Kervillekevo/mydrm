from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

# Only import the views you need
from videos.views import serve_aes_key, serve_hls_segment, serve_hls_playlist

@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('videos/', include('videos.urls')),
    path("csrf/", get_csrf),
    
    # HLS media serving URLs (token-auth protected in views)
    path(
        'media/videos/hls/<uuid:video_id>/<uuid:key_id>.key',  # ✅ key_id accepted
        serve_aes_key,
        name='serve_aes_key'
    ),
    path(
        'media/videos/hls/<uuid:video_id>/<str:quality>/<str:segment_name>.ts',
        serve_hls_segment,
        name='serve_hls_segment'
    ),
    path(
        'media/videos/hls/<uuid:video_id>/<str:quality>/playlist.m3u8',
        serve_hls_playlist,
        name='serve_hls_playlist'
    ),
]

# Serve media files in development (includes .m3u8 and .ts from MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
