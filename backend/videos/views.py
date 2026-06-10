import os
import logging
import time
import secrets

from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.core.cache import cache

from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, authentication_classes

from .models import Video
from .serializers import VideoSerializer
from .security import (
    generate_stream_token,
    validate_stream_token,
    acquire_segment_slot,
    release_segment_slot,
)

logger = logging.getLogger(__name__)


def disable_cache(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    response["X-Accel-Buffering"] = "no"
    return response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_stream_token(request, video_id):
    token = generate_stream_token(
        video_id=str(video_id),
        resource_type="playlist",
        request=request,
        ttl=120,
    )
    return disable_cache(HttpResponse(token, content_type="text/plain"))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_aes_key(request, video_id):
    token = request.GET.get("token")

    if not validate_stream_token(
        token=token,
        video_id=str(video_id),
        resource_type="key",
        request=request,
    ):
        raise Http404("Invalid token")

    key_path = os.path.join(
        settings.MEDIA_ROOT, "videos", "keys", f"{video_id}.key"
    )

    if not os.path.exists(key_path):
        raise Http404("Key not found")

    response = FileResponse(open(key_path, "rb"), content_type="application/octet-stream")
    return disable_cache(response)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_segment_alias(request, alias):
    data = cache.get(f"seg:{alias}")

    if not data:
        return HttpResponse(status=410)

    cache.delete(f"seg:{alias}")

    if time.time() > data.get("expires", 0):
        return HttpResponse(status=410)

    video_id = data["video_id"]
    quality = data["quality"]
    seg_name = data["seg_name"]

    segment_path = os.path.join(
        settings.MEDIA_ROOT,
        "videos",
        "hls",
        video_id,
        quality,
        seg_name,
    )

    if not os.path.exists(segment_path):
        raise Http404("Segment not found")

    response = FileResponse(
        open(segment_path, "rb"),
        content_type="application/octet-stream",
        as_attachment=False,
    )
    return disable_cache(response)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_segment(request, video_id, quality, segment_name):
    return HttpResponse(status=410)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_hls_playlist(request, video_id, quality):
    token = request.GET.get("token")

    if not validate_stream_token(
        token=token,
        video_id=str(video_id),
        resource_type="playlist",
        resource_name=quality,
        request=request,
    ):
        raise Http404("Invalid token")

    playlist_path = os.path.join(
        settings.MEDIA_ROOT,
        "videos",
        "hls",
        str(video_id),
        quality,
        "playlist.m3u8",
    )

    if not os.path.exists(playlist_path):
        raise Http404("Playlist not found")

    with open(playlist_path) as f:
        lines = f.readlines()

    rewritten = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#EXT-X-KEY"):
            key_token = generate_stream_token(
                video_id=str(video_id),
                resource_type="key",
                request=request,
                ttl=120,
            )
            new_key_line = f'#EXT-X-KEY:METHOD=AES-128,URI="/videos/media/{video_id}/key?token={key_token}",IV=0x00000000000000000000000000000000'
            rewritten.append(new_key_line)
            continue

        if stripped.endswith(".ts"):
            alias = secrets.token_hex(12)
            cache.set(
                f"seg:{alias}",
                {
                    "video_id": str(video_id),
                    "quality": quality,
                    "seg_name": stripped,
                    "expires": time.time() + 10,
                },
                timeout=10,
            )
            rewritten.append(f"/videos/media/chunk/{alias}.bin")
            continue

        rewritten.append(stripped)

    response = HttpResponse(
        "\n".join(rewritten),
        content_type="text/plain",
    )
    return disable_cache(response)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def serve_master_playlist(request, video_id):
    base_path = os.path.join(
        settings.MEDIA_ROOT, "videos", "hls", str(video_id)
    )

    variants = [
        ("240p", 500000, "426x240"),
        ("360p", 1000000, "640x360"),
        ("480p", 1600000, "854x480"),
        ("720p", 3000000, "1280x720"),
    ]

    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]

    for quality, bw, res in variants:
        if os.path.exists(os.path.join(base_path, quality, "playlist.m3u8")):
            variant_token = generate_stream_token(
                video_id=str(video_id),
                resource_type="playlist",
                resource_name=quality,
                request=request,
                ttl=120,
            )
            lines.extend([
                f"#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={res}",
                f"/videos/media/{video_id}/{quality}/data?token={variant_token}",
            ])

    return disable_cache(HttpResponse(
        "\n".join(lines),
        content_type="text/plain",
    ))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def embed_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    allowed_origins = getattr(settings, "ALLOWED_EMBED_ORIGINS", [
    "http://localhost",
    "http://127.0.0.1",
])
    referer = request.META.get("HTTP_REFERER", "")
    origin = request.META.get("HTTP_ORIGIN", "")

    if not any(o in (referer + origin) for o in allowed_origins):
        raise Http404("Invalid embed origin")

    token = generate_stream_token(
        video_id=str(video.id),
        resource_type="playlist",
        request=request,
        ttl=120,
    )

    master_url = request.build_absolute_uri(
        f"/videos/media/{video.id}/manifest?token={token}"
    )

    html = render_to_string(
        "videos/embed.html",
        {
            "video": video,
            "master_playlist_url": master_url,
            "poster_url": video.poster_url(),
        },
    )

    return disable_cache(HttpResponse(html, content_type="text/html"))


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Video.objects.filter(status="ready")
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]