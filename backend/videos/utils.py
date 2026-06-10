import os
import subprocess
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from videos.models import Video

logger = logging.getLogger(__name__)


# ======================
# PATCH PLAYLIST TOKENS
# ======================
def patch_hls_tokens(hls_root):
    """
    Replace FFmpeg placeholders with a neutral marker.
    Real tokens are injected at request-time in views.py.
    """
    for root, _, files in os.walk(hls_root):
        for file in files:
            if file.endswith(".m3u8"):
                path = os.path.join(root, file)

                with open(path, "r") as f:
                    content = f.read()

                # Keep placeholder — DO NOT inject real tokens here
                content = content.replace("REPLACE_ME", "__TOKEN__")

                with open(path, "w") as f:
                    f.write(content)


# ======================
# MASTER PLAYLIST
# ======================
def rebuild_master_playlist(video: Video):
    output_dir = os.path.join(settings.MEDIA_ROOT, video.hls_output_dir)
    master_path = os.path.join(output_dir, "master.m3u8")

    rendition_map = {
        "240p": ("426x240", 500000),
        "360p": ("640x360", 1000000),
        "480p": ("854x480", 1600000),
        "720p": ("1280x720", 3000000),
    }

    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]

    for rendition, (resolution, bandwidth) in rendition_map.items():
        playlist_path = os.path.join(output_dir, rendition, "playlist.m3u8")
        if os.path.exists(playlist_path):
            lines.append(
                f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}"
            )
            lines.append(f"{rendition}/playlist.m3u8")

    with open(master_path, "w") as f:
        f.write("\n".join(lines))


# ======================
# ENCODER
# ======================
def encode_rendition(r, input_file, hls_output_dir, key_info_path):
    try:
        rendition_dir = os.path.join(hls_output_dir, r["name"])
        os.makedirs(rendition_dir, exist_ok=True)

        playlist_path = os.path.join(rendition_dir, "playlist.m3u8")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-vf", f"scale={r['resolution']}",
            "-c:a", "aac",
            "-ar", "48000",
            "-b:a", "128k",
            "-c:v", "h264",
            "-preset", "ultrafast",
            "-profile:v", "main",
            "-crf", "25",
            "-sc_threshold", "0",
            "-g", "30",
            "-b:v", r["bitrate"],
            "-hls_time", "6",
            "-hls_playlist_type", "vod",

            # 🔥 THIS IS THE FIX
            "-start_number", "0",
            
            "-hls_segment_filename",
            os.path.join(rendition_dir, "segment_%03d.ts"),
            "-hls_key_info_file", key_info_path,
            playlist_path,
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1800
        )

        if result.returncode != 0:
            logger.error(result.stderr[-500:])
            return False, r["name"]

        return True, r["name"]

    except Exception as e:
        logger.exception(e)
        return False, r["name"]


# ======================
# MAIN PIPELINE
# ======================
def process_video(video_id):
    video = Video.objects.get(id=video_id)
    video.status = "processing"
    video.save(update_fields=["status"])

    input_file = video.uploaded_file.path

    hls_output_dir = os.path.join(
        settings.MEDIA_ROOT, "videos", "hls", str(video.id)
    )
    os.makedirs(hls_output_dir, exist_ok=True)

    key_dir = os.path.join(settings.MEDIA_ROOT, "videos", "keys")
    os.makedirs(key_dir, exist_ok=True)


    key_path = os.path.join(key_dir, f"{video.id}.key")
    with open(key_path, "wb") as f:
        f.write(os.urandom(16))

    key_info_path = os.path.join(hls_output_dir, f"{video.id}.keyinfo")

    key_url = f"/videos/media/{video.id}/key?token=REPLACE_ME"
    with open(key_info_path, "w") as f:
        f.write(
            f"{key_url}\n"
            f"{key_path}\n"
            "\n"
        )

    renditions = [
        {"name": "240p", "resolution": "426:240", "bitrate": "400k"},
        {"name": "360p", "resolution": "640:360", "bitrate": "800k"},
        {"name": "480p", "resolution": "854:480", "bitrate": "1400k"},
        {"name": "720p", "resolution": "1280:720", "bitrate": "2800k"},
    ]

    encode_rendition(
        renditions[0], input_file, hls_output_dir, key_info_path
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                encode_rendition, r, input_file, hls_output_dir, key_info_path
            )
            for r in renditions[1:]
        ]
        for f in as_completed(futures):
            f.result()

    patch_hls_tokens(hls_output_dir)

    # SAVE PATHS FIRST
    video.hls_output_dir = f"videos/hls/{video.id}"
    video.aes_key_path = f"videos/keys/{video.id}.key"
    video.status = "ready"
    video.save(
        update_fields=["status", "hls_output_dir", "aes_key_path"]
    )

    rebuild_master_playlist(video)

    os.remove(key_info_path)

