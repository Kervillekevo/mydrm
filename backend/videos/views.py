import os
import logging
import mimetypes
import base64
from urllib.parse import unquote

from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.loader import render_to_string

from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response

from .models import Video
from .serializers import VideoSerializer

logger = logging.getLogger(__name__)

# --- AES Key ---
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_aes_key(request, video_id):
    logger.info("🔑 AES key request for video_id: %s", video_id)
    try:
        video = get_object_or_404(Video, id=video_id)
        # Check multiple possible locations
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
        raise Http404("Key not found")
    except Video.DoesNotExist:
        raise Http404("Video not found")
    except Exception as e:
        logger.error(f"Unexpected error serving AES key: {str(e)}")
        raise Http404("Internal error")


# --- HLS Segment ---
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_segment(request, video_id, quality, segment_name):
    video = get_object_or_404(Video, id=video_id)
    segment_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), quality, f"{segment_name}.ts")
    if os.path.exists(segment_path):
        mime_type, _ = mimetypes.guess_type(segment_path)
        if not mime_type:
            mime_type = 'video/MP2T'
        response = FileResponse(open(segment_path, 'rb'), content_type=mime_type)
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    raise Http404("Segment not found")


# --- HLS Playlist ---
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_playlist(request, video_id, quality):
    video = get_object_or_404(Video, id=video_id)
    playlist_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), quality, 'playlist.m3u8')
    if not os.path.exists(playlist_path):
        raise Http404("Playlist not found")
    response = FileResponse(open(playlist_path, 'rb'), content_type='application/vnd.apple.mpegurl')
    response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response['Access-Control-Allow-Credentials'] = 'true'
    return response


# --- Master Playlist ---
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_master_playlist(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    quality_variants = [
        {'quality': '240p', 'bandwidth': 500000, 'resolution': '426x240'},
        {'quality': '360p', 'bandwidth': 1000000, 'resolution': '640x360'},
        {'quality': '480p', 'bandwidth': 1600000, 'resolution': '854x480'},
        {'quality': '720p', 'bandwidth': 3000000, 'resolution': '1280x720'},
    ]
    playlist_lines = ['#EXTM3U', '#EXT-X-VERSION:3', '']
    base_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id))
    for variant in quality_variants:
        variant_path = os.path.join(base_path, variant['quality'], 'playlist.m3u8')
        if os.path.exists(variant_path):
            playlist_lines.extend([
                f"#EXT-X-STREAM-INF:BANDWIDTH={variant['bandwidth']},RESOLUTION={variant['resolution']}",
                f"/secure/hls/{video.id}/{variant['quality']}/playlist.m3u8",
                ''
            ])
    if len([l for l in playlist_lines if 'EXT-X-STREAM-INF' in l]) == 0:
        raise Http404("No quality variants available")
    response = HttpResponse('\n'.join(playlist_lines), content_type='application/vnd.apple.mpegurl')
    response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# --- Secure File Response (base64 support) ---
@csrf_exempt
def secure_file_response(request: HttpRequest, encoded_path: str):
    """
    Decodes base64 paths and routes to master playlist view.
    Example encoded_path -> /secure/hls/<base64(master_path)>
    """
    try:
        encoded_path = unquote(encoded_path)
        padding = '=' * (-len(encoded_path) % 4)
        decoded_path = base64.urlsafe_b64decode(encoded_path + padding).decode("utf-8")
        logger.info(f"Decoded secure path: {decoded_path}")
        # Only handle master.m3u8 for now
        if decoded_path.startswith('/media/videos/hls/') and decoded_path.endswith('master.m3u8'):
            parts = decoded_path.strip('/').split('/')
            video_id = parts[3]
            return serve_master_playlist(request, video_id)
        raise Http404("Unsupported secure path")
    except Exception as e:
        logger.error(f"Failed to decode secure URL: {str(e)}")
        raise Http404("Invalid or corrupted secure URL")


# --- Embed Video ---
@xframe_options_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def embed_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    # Build absolute master playlist URL
    base_url = "http://104.152.49.62"  # your live server
    master_playlist_url = f"{base_url}/secure/hls/{video.id}/master.m3u8"

    html = render_to_string("videos/embed.html", {
        'video': video,
        'master_playlist_url': master_playlist_url,
        'poster_url': video.poster_url(),
        'token': request.GET.get("token", ""),
    })

    return HttpResponse(html, content_type="text/html")


# --- ViewSet ---
class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
