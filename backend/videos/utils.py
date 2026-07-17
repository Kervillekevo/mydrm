import os
import logging
import requests

from django.conf import settings
from videos.models import Video

logger = logging.getLogger(__name__)

FFMATE_URL = getattr(settings, "FFMATE_URL", "http://localhost:8001")


def patch_hls_tokens(hls_root):
    for root, _, files in os.walk(hls_root):
        for file in files:
            if file.endswith(".m3u8"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                content = content.replace("REPLACE_ME", "__TOKEN__")
                with open(path, "w") as f:
                    f.write(content)


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
            lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}")
            lines.append(f"{rendition}/playlist.m3u8")

    with open(master_path, "w") as f:
        f.write("\n".join(lines))


def process_video(video_id):
    video = Video.objects.get(id=video_id)
    video.status = "processing"
    video.save(update_fields=["status"])

    input_file = video.uploaded_file.path

    hls_output_dir = os.path.join(settings.MEDIA_ROOT, "videos", "hls", str(video.id))
    os.makedirs(hls_output_dir, exist_ok=True)

    key_dir = os.path.join(settings.MEDIA_ROOT, "videos", "keys")
    os.makedirs(key_dir, exist_ok=True)

    key_path = os.path.join(key_dir, f"{video.id}.key")
    with open(key_path, "wb") as f:
        f.write(os.urandom(16))

    key_info_path = os.path.join(hls_output_dir, f"{video.id}.keyinfo")
    key_url = f"/videos/media/{video.id}/key?token=REPLACE_ME"
    with open(key_info_path, "w") as f:
        f.write(f"{key_url}\n{key_path}\n\n")

    renditions = [
        {"name": "240p", "resolution": "426:240", "bitrate": "400k"},
        {"name": "360p", "resolution": "640:360", "bitrate": "800k"},
        {"name": "480p", "resolution": "854:480", "bitrate": "1400k"},
        {"name": "720p", "resolution": "1280:720", "bitrate": "2800k"},
    ]

    task_ids = []

    for r in renditions:
        rendition_dir = os.path.join(hls_output_dir, r["name"])
        os.makedirs(rendition_dir, exist_ok=True)
        playlist_path = os.path.join(rendition_dir, "playlist.m3u8")
        segment_pattern = os.path.join(rendition_dir, "segment_%03d.ts")

        cmd = (
            f"-vf scale={r['resolution']} "
            f"-c:a aac -ar 48000 -b:a 128k "
            f"-c:v h264 -preset ultrafast -profile:v main "
            f"-crf 25 -sc_threshold 0 -g 30 -b:v {r['bitrate']} "
            f"-hls_time 6 -hls_playlist_type vod -start_number 0 "
            f"-hls_segment_filename {segment_pattern} "
            f"-hls_key_info_file {key_info_path} "
            f"${{OUTPUT_FILE}}"
        )

        payload = {
            "name": f"{video.id}-{r['name']}",
            "inputFile": input_file,
            "outputFile": playlist_path,
            "command": f"-i ${{INPUT_FILE}} {cmd}",
            "metadata": {
                "video_id": str(video.id),
                "rendition": r["name"],
            },
        }

        try:
            res = requests.post(
                f"{FFMATE_URL}/api/v1/tasks",
                json=payload,
                timeout=10,
            )
            if res.status_code in (200, 201):
                task_data = res.json()
                task_ids.append(task_data.get("uuid"))
                logger.info(f"FFmate task created for {r['name']}: {task_data.get('uuid')}")
            else:
                logger.error(f"FFmate task creation failed for {r['name']}: {res.text}")
        except Exception as e:
            logger.exception(f"FFmate request failed for {r['name']}: {e}")

    video.hls_output_dir = f"videos/hls/{video.id}"
    video.aes_key_path = f"videos/keys/{video.id}.key"
    video.save(update_fields=["hls_output_dir", "aes_key_path"])

    logger.info(f"Video {video.id} submitted to FFmate with {len(task_ids)} tasks")