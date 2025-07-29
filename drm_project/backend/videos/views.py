import os
import logging
import mimetypes
import base64
from urllib.parse import unquote

from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404

from django.http import Http404, HttpRequest
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponseRedirect

from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from .models import Video
from .serializers import VideoSerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_aes_key(request, video_id):
    logger.debug("🔑 AES key request | User: %s | Auth: %s", request.user, request.auth)

    video = get_object_or_404(Video, id=video_id)

    # Build the absolute path to the AES key (e.g., MEDIA_ROOT/videos/keys/<video_id>.key)
    key_path = os.path.join(settings.MEDIA_ROOT, video.aes_key_path)
    logger.debug("🔑 Looking for AES key at: %s", key_path)

    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            key_data = f.read()

        response = HttpResponse(key_data, content_type='application/octet-stream')
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

    logger.error("❌ Key file not found: %s", key_path)
    raise Http404("Key not found")


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_segment(request, video_id, quality, segment_name):
    logger.debug("📽 HLS segment request | User: %s | Auth: %s", request.user, request.auth)

    video = get_object_or_404(Video, id=video_id)

    full_segment_name = f"{segment_name}.ts"
    segment_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), quality, full_segment_name)

    if os.path.exists(segment_path):
        mime_type, _ = mimetypes.guess_type(segment_path)
        if not mime_type:
            mime_type = 'video/MP2T'

        response = FileResponse(open(segment_path, 'rb'), content_type=mime_type)
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

    logger.error("❌ Segment file not found: %s", segment_path)
    raise Http404("Segment not found")



@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_playlist(request, video_id, quality):
    logger.debug("📺 HLS playlist request | User: %s | Video: %s | Quality: %s", request.user, video_id, quality)

    video = get_object_or_404(Video, id=video_id)

    playlist_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), quality, 'playlist.m3u8')

    if not os.path.exists(playlist_path):
        logger.error("❌ Playlist not found at: %s", playlist_path)
        raise Http404("Playlist not found")

    try:
        response = FileResponse(open(playlist_path, 'rb'), content_type='application/vnd.apple.mpegurl')
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    except Exception as e:
        logger.exception("🔥 Failed to serve playlist: %s", str(e))
        return Response({"detail": "Internal server error"}, status=500)



@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_master_playlist(request, video_id):
    """
    Dynamically generates master HLS playlist that references all quality variants
    using absolute URLs so that relative paths don't cause 404s.
    """
    logger.debug("🎬 Master playlist request | User: %s | Video: %s", request.user, video_id)
    
    try:
        video = get_object_or_404(Video, id=video_id)

        # Define quality variants
        quality_variants = [
            {'quality': '240p', 'bandwidth': 500000, 'resolution': '426x240'},
            {'quality': '360p', 'bandwidth': 1000000, 'resolution': '640x360'},
            {'quality': '480p', 'bandwidth': 1600000, 'resolution': '854x480'},
            {'quality': '720p', 'bandwidth': 3000000, 'resolution': '1280x720'},
        ]

        # Build master playlist
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
                logger.info(f"✅ Added {variant['quality']} variant")
            else:
                logger.warning(f"⚠️ Missing {variant['quality']} at {variant_path}")

        if len([l for l in playlist_lines if 'EXT-X-STREAM-INF' in l]) == 0:
            logger.error(f"❌ No variants found for video {video_id}")
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

    except Video.DoesNotExist:
        logger.error(f"❌ Video {video_id} not found")
        raise Http404("Video not found")
    except Exception as e:
        logger.error(f"❌ Error serving master playlist: {str(e)}")
        raise Http404("Internal error")

@csrf_exempt
def secure_file_response(request: HttpRequest, encoded_path: str):
    try:
        encoded_path = unquote(encoded_path)

        # Fix base64 padding
        padding = '=' * (-len(encoded_path) % 4)
        decoded_path = base64.urlsafe_b64decode(encoded_path + padding).decode("utf-8")

        logger.info(f"✅ Decoded path: {decoded_path}")

        # Handle only master.m3u8 files for now
        if decoded_path.startswith('/media/videos/hls/') and decoded_path.endswith('master.m3u8'):
            # Example: /media/videos/hls/<video_id>/master.m3u8
            parts = decoded_path.strip('/').split('/')
            video_id = parts[3]  # 0=media, 1=videos, 2=hls, 3=<video_id>
            return serve_master_playlist(request, video_id=video_id)

        raise Http404("Unsupported secure path")

    except Exception as e:
        logger.error(f"❌ Failed to decode secure URL: {str(e)}")
        raise Http404("Invalid or corrupted secure URL")
    
class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
