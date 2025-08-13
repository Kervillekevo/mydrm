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

from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.loader import render_to_string

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
    logger.info("🔑 DEBUG: AES key request for video_id: %s", video_id)
    
    try:
        video = get_object_or_404(Video, id=video_id)
        logger.info("✅ DEBUG: Video found - status: %s", video.status)
        logger.info("✅ DEBUG: Video.aes_key_path: %s", video.aes_key_path)
        
        # Check multiple possible locations
        possible_paths = [
            # Where your processing puts it (parent HLS dir)
            os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', f'{video_id}.key'),
            # Where your processing puts it (video-specific HLS dir)  
            os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video_id), f'{video_id}.key'),
            # Where your model says it should be
            os.path.join(settings.MEDIA_ROOT, video.aes_key_path) if video.aes_key_path else None,
            # Original keys directory
            os.path.join(settings.MEDIA_ROOT, 'videos', 'keys', f'{video_id}.key'),
        ]
        
        # Remove None values
        possible_paths = [p for p in possible_paths if p]
        
        logger.info("🔍 DEBUG: Checking these paths:")
        for i, path in enumerate(possible_paths):
            exists = os.path.exists(path)
            logger.info("   %d. %s - EXISTS: %s", i+1, path, exists)
            if exists:
                try:
                    file_size = os.path.getsize(path)
                    logger.info("      File size: %d bytes", file_size)
                except Exception as e:
                    logger.error("      Error getting file size: %s", e)
        
        # Try each path
        for path in possible_paths:
            if os.path.exists(path):
                logger.info("✅ DEBUG: Using key from: %s", path)
                try:
                    with open(path, 'rb') as f:
                        key_data = f.read()
                    
                    logger.info("✅ DEBUG: Successfully read %d bytes", len(key_data))
                    
                    response = HttpResponse(key_data, content_type='application/octet-stream')
                    response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
                    response['Access-Control-Allow-Credentials'] = 'true'
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    return response
                except Exception as e:
                    logger.error("❌ DEBUG: Error reading key file %s: %s", path, str(e))
                    continue
        
        # If we get here, no key was found
        logger.error("❌ DEBUG: No key file found in any location!")
        
        # Let's also check what directories exist
        hls_base = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls')
        if os.path.exists(hls_base):
            logger.info("📁 DEBUG: HLS base directory contents:")
            try:
                for item in os.listdir(hls_base):
                    item_path = os.path.join(hls_base, item)
                    is_dir = os.path.isdir(item_path)
                    logger.info("   - %s %s", item, "(DIR)" if is_dir else "(FILE)")
            except Exception as e:
                logger.error("   Error reading HLS directory: %s", e)
        else:
            logger.error("📁 DEBUG: HLS base directory doesn't exist: %s", hls_base)
        
        raise Http404("Key not found")
        
    except Video.DoesNotExist:
        logger.error("❌ DEBUG: Video with id %s not found", video_id)
        raise Http404("Video not found")
    except Exception as e:
        logger.error("❌ DEBUG: Unexpected error: %s", str(e))
        raise Http404("Internal error")


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
                logger.warning(f"⚠ Missing {variant['quality']} at {variant_path}")

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
    

@xframe_options_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def embed_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    return HttpResponse(
        render_to_string("videos/embed.html", {
            'video': video,
            'master_playlist_url': f"/secure/hls/{video.id}/master.m3u8",
            'poster_url': video.poster_url(),
            'token': request.GET.get("token", ""),
        }),
        content_type="text/html"
    )
  
class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]