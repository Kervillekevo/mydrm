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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def serve_master_playlist(request, video_id):
    """
    Dynamically generates master HLS playlist that references all quality variants
    """
    logger.debug("🎬 Master playlist request | User: %s | Video: %s", request.user, video_id)
    
    try:
        # Get video instance to verify ownership/permissions
        video = get_object_or_404(Video, id=video_id)
        
        # Define available qualities and their properties
        quality_variants = [
            {
                'quality': '240p',
                'bandwidth': 500000,
                'resolution': '426x240'
            },
            {
                'quality': '360p', 
                'bandwidth': 1000000,
                'resolution': '640x360'
            },
            {
                'quality': '480p',
                'bandwidth': 1600000,
                'resolution': '854x480'  
            },
            {
                'quality': '720p',
                'bandwidth': 3000000,
                'resolution': '1280x720'
            }
        ]
        
        # Build master playlist content
        playlist_lines = [
            '#EXTM3U',
            '#EXT-X-VERSION:3',
            ''
        ]
        
        # Check which quality variants actually exist
        base_path = os.path.join(
            settings.MEDIA_ROOT,
            'videos', 'hls', 
            str(video_id)
        )
        
        for variant in quality_variants:
            quality_playlist_path = os.path.join(
                base_path, 
                variant['quality'], 
                'playlist.m3u8'
            )
            
            # Only include qualities that exist on disk
            if os.path.exists(quality_playlist_path):
                playlist_lines.extend([
                    f"#EXT-X-STREAM-INF:BANDWIDTH={variant['bandwidth']},RESOLUTION={variant['resolution']}",
                    f"{variant['quality']}/playlist.m3u8",
                    ''
                ])
                logger.info(f"✅ Added {variant['quality']} variant to master playlist")
            else:
                logger.warning(f"⚠️ Missing {variant['quality']} variant at {quality_playlist_path}")
        
        # Join all lines
        playlist_content = '\n'.join(playlist_lines)
        
        if len([line for line in playlist_lines if 'EXT-X-STREAM-INF' in line]) == 0:
            logger.error(f"❌ No quality variants found for video {video_id}")
            raise Http404("No video quality variants available")
        
        # Create HTTP response
        response = HttpResponse(
            playlist_content,
            content_type='application/vnd.apple.mpegurl'
        )
        
        # Set CORS headers
        response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Credentials'] = 'true'
        
        # Set caching headers
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        logger.info(f"✅ Served dynamically generated master playlist for video {video_id}")
        return response
        
    except Video.DoesNotExist:
        logger.error(f"❌ Video {video_id} not found")
        raise Http404("Video not found")
        
    except Exception as e:
        logger.error(f"❌ Error serving master playlist for video {video_id}: {str(e)}")
        raise Http404("Error serving master playlist")
    

class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
