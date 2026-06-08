import os
import logging
import mimetypes
import base64
import time
import secrets
from urllib.parse import unquote

from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.loader import render_to_string
from django.core.cache import cache

from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from .models import Video
from .serializers import VideoSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 🔑  AES Key — unchanged logic, just tightened headers
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_aes_key(request, video_id):
    logger.info("🔑 AES key request for video_id: %s", video_id)

    try:
        video = get_object_or_404(Video, id=video_id)

        possible_paths = [
            os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', f'{video_id}.key'),
            os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), f'{video_id}.key'),
            os.path.join(settings.MEDIA_ROOT, video.aes_key_path) if video.aes_key_path else None,
            os.path.join(settings.MEDIA_ROOT, 'videos', 'keys', f'{video_id}.key'),
        ]
        possible_paths = [p for p in possible_paths if p]

        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    key_data = f.read()

                response = HttpResponse(key_data, content_type='application/octet-stream')
                response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return response

        logger.error("❌ No key file found for video %s", video_id)
        raise Http404("Key not found")

    except Exception as e:
        logger.error("❌ AES key error: %s", str(e))
        raise Http404("Internal error")


# ---------------------------------------------------------------------------
# 🎬  Master playlist
#     CHANGE 1: served as text/plain  →  VDH does NOT recognise it as HLS
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_master_playlist(request, video_id):
    logger.debug("🎬 Master playlist | video: %s", video_id)

    try:
        video = get_object_or_404(Video, id=video_id)

        quality_variants = [
            {'quality': '240p',  'bandwidth': 500000,  'resolution': '426x240'},
            {'quality': '360p',  'bandwidth': 1000000, 'resolution': '640x360'},
            {'quality': '480p',  'bandwidth': 1600000, 'resolution': '854x480'},
            {'quality': '720p',  'bandwidth': 3000000, 'resolution': '1280x720'},
        ]

        playlist_lines = ['#EXTM3U', '#EXT-X-VERSION:3', '']
        base_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id))

        for variant in quality_variants:
            variant_path = os.path.join(base_path, variant['quality'], 'playlist.m3u8')
            if os.path.exists(variant_path):
                playlist_lines.extend([
                    f"#EXT-X-STREAM-INF:BANDWIDTH={variant['bandwidth']},RESOLUTION={variant['resolution']}",
                    # ✅ CHANGE 1: point to the new extension-less quality URL
                    f"/api/stream/{video.id}/{variant['quality']}/index",
                    ''
                ])

        if not any('EXT-X-STREAM-INF' in l for l in playlist_lines):
            raise Http404("No quality variants available")

        response = HttpResponse(
            '\n'.join(playlist_lines),
            # ✅ CHANGE 1: text/plain  →  VDH ignores this completely
            content_type='text/plain',
        )
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    except Exception as e:
        logger.error("❌ Master playlist error: %s", str(e))
        raise Http404("Internal error")


# ---------------------------------------------------------------------------
# 📺  Quality playlist
#     CHANGE 2: served as text/plain AND segment URLs use single-use aliases
#               ending in .bin (not .ts)  →  VDH can't identify or replay them
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_playlist(request, video_id, quality):
    logger.debug("📺 Quality playlist | video: %s | quality: %s", video_id, quality)

    video = get_object_or_404(Video, id=video_id)
    playlist_path = os.path.join(
        settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), quality, 'playlist.m3u8'
    )

    if not os.path.exists(playlist_path):
        raise Http404("Playlist not found")

    try:
        with open(playlist_path, 'r') as f:
            original = f.read()

        new_lines = []
        for line in original.splitlines():
            line = line.strip()

            # Rewrite the AES key URI so it goes through our protected endpoint
            if line.startswith('#EXT-X-KEY'):
                new_lines.append(
                    f'#EXT-X-KEY:METHOD=AES-128,'
                    f'URI="/api/stream/{video_id}/key",'
                    f'IV=0x00000000000000000000000000000000'
                )

            # ✅ CHANGE 2a: replace every .ts segment reference with a
            #    single-use alias that expires in 10 seconds
            elif line.endswith('.ts'):
                # Extract the original segment filename without extension
                seg_name = os.path.splitext(os.path.basename(line))[0]

                alias = secrets.token_hex(12)   # e.g. "a3f9b2c1d4e5f6a7b8c9d0e1"
                cache.set(
                    f"seg:{alias}",
                    {
                        'video_id': str(video_id),
                        'quality':  quality,
                        'seg_name': seg_name,       # the real segment name
                        'expires':  time.time() + 10,
                    },
                    timeout=10                      # Redis/memcached TTL
                )

                # ✅ CHANGE 2b: .bin extension  →  VDH doesn't recognise segment type
                new_lines.append(f'/api/stream/chunk/{alias}.bin')

            else:
                new_lines.append(line)

        response = HttpResponse(
            '\n'.join(new_lines),
            # ✅ CHANGE 2c: text/plain  →  VDH ignores non-HLS MIME types
            content_type='text/plain',
        )
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    except Exception as e:
        logger.exception("🔥 Failed to serve quality playlist: %s", str(e))
        return Response({"detail": "Internal server error"}, status=500)


# ---------------------------------------------------------------------------
# 🎞  Segment serving via single-use alias
#     CHANGE 3: alias is deleted on first use — replayed URLs return 410 Gone
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_segment_alias(request, alias):
    """
    Serves a video segment using a single-use alias.
    The alias is created in serve_hls_playlist() and expires in 10 seconds.
    VDH captures the alias URL from the playlist but by the time its
    companion app tries to download it, the alias is already gone.
    """
    data = cache.get(f"seg:{alias}")

    if not data:
        # Alias expired or already used — return 410 Gone
        logger.warning("⚠ Dead alias requested: %s", alias)
        return HttpResponse(status=410)

    # ✅ Delete immediately — single use only
    cache.delete(f"seg:{alias}")

    # Check alias hasn't expired (belt-and-suspenders on top of cache TTL)
    if time.time() > data.get('expires', 0):
        return HttpResponse(status=410)

    video_id = data['video_id']
    quality  = data['quality']
    seg_name = data['seg_name']

    segment_path = os.path.join(
        settings.MEDIA_ROOT, 'videos', 'hls',
        video_id, quality, f"{seg_name}.ts"
    )

    if not os.path.exists(segment_path):
        logger.error("❌ Segment file not found: %s", segment_path)
        raise Http404("Segment not found")

    # ✅ CHANGE 3: serve as generic binary — not video/mp2t
    response = FileResponse(open(segment_path, 'rb'), content_type='application/octet-stream')
    response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response['Access-Control-Allow-Credentials'] = 'true'
    return response


# ---------------------------------------------------------------------------
# 🔒  Legacy segment endpoint (kept so old URLs don't hard-crash)
#     Now returns 410 Gone — tells the player to re-fetch the playlist
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_segment(request, video_id, quality, segment_name):
    """
    Old direct segment endpoint.
    We return 410 Gone instead of serving the file.
    The Video.js player will reload the playlist and get fresh aliases.
    """
    logger.warning("⚠ Direct segment access attempted (old URL): %s/%s/%s", video_id, quality, segment_name)
    return HttpResponse(status=410)


# ---------------------------------------------------------------------------
# 🔐  Secure file response (kept exactly as before)
# ---------------------------------------------------------------------------

@csrf_exempt
def secure_file_response(request: HttpRequest, encoded_path: str):
    try:
        encoded_path = unquote(encoded_path)
        padding = '=' * (-len(encoded_path) % 4)
        decoded_path = base64.urlsafe_b64decode(encoded_path + padding).decode("utf-8")

        if decoded_path.startswith('/media/videos/hls/') and decoded_path.endswith('master.m3u8'):
            parts = decoded_path.strip('/').split('/')
            video_id = parts[3]
            return serve_master_playlist(request, video_id=video_id)

        raise Http404("Unsupported secure path")

    except Exception as e:
        logger.error("❌ Failed to decode secure URL: %s", str(e))
        raise Http404("Invalid or corrupted secure URL")


# ---------------------------------------------------------------------------
# 📺  Embed view (unchanged)
# ---------------------------------------------------------------------------

@xframe_options_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def embed_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    return HttpResponse(
        render_to_string("videos/embed.html", {
            'video':               video,
            'master_playlist_url': f"/api/stream/{video.id}/master",
            'poster_url':          video.poster_url(),
            'token':               request.GET.get("token", ""),
        }),
        content_type="text/html"
    )


# ---------------------------------------------------------------------------
# 📋  VideoViewSet (unchanged)
# ---------------------------------------------------------------------------

class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]