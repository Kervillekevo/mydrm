import os
import logging
import mimetypes

from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from .models import Video
from .serializers import VideoSerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def serve_aes_key(request, video_id, key_id):  # ✅ key_id added to match new URL
    """
    Serve the AES key file for a given video,
    only if the user is authenticated and is the owner.
    """
    logger.debug("🔑 AES key request | User: %s | Auth: %s", request.user, request.auth)

    video = get_object_or_404(Video, id=video_id)
    if video.owner != request.user:
        return Response({"detail": "Not allowed"}, status=403)

    # Updated to use key_id from the URL
    key_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), f"{key_id}.key")
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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def serve_hls_segment(request, video_id, quality, segment_name):
    """
    Serve an HLS .ts segment for a given video,
    only if the user is authenticated and is the owner.
    """
    logger.debug("📽 HLS segment request | User: %s | Auth: %s", request.user, request.auth)

    video = get_object_or_404(Video, id=video_id)
    if video.owner != request.user:
        return Response({"detail": "Not allowed"}, status=403)

    full_segment_name = f"{segment_name}.ts"

    segment_path = os.path.join(
        settings.MEDIA_ROOT,
        'videos', 'hls',
        str(video_id),
        quality,
        full_segment_name
    )

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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def serve_hls_playlist(request, video_id, quality):
    """
    Serves the HLS .m3u8 playlist file for the given video and quality.
    Path: /media/videos/hls/<video_id>/<quality>/playlist.m3u8
    """
    logger.debug("📺 HLS playlist request | User: %s | Video: %s | Quality: %s", request.user, video_id, quality)

    # Ensure video exists and belongs to the user
    video = get_object_or_404(Video, id=video_id)
    if video.owner != request.user:
        logger.warning("🚫 Unauthorized playlist access | User: %s | Video owner: %s", request.user, video.owner)
        return Response({"detail": "Not allowed"}, status=403)

    # Build full path to playlist
    playlist_path = os.path.join(
        settings.MEDIA_ROOT,
        'videos', 'hls',
        str(video_id),
        quality,
        'playlist.m3u8'
    )

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


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
