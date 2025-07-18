import os
import subprocess
import uuid
import logging

from django.conf import settings
from videos.models import Video

logger = logging.getLogger(_name_)

def process_video(video_id):
    logger.info(f"🚀 Starting process_video for {video_id}")

    video = None  # ✅ Always initialize!
    try:
        video = Video.objects.get(id=video_id)

        input_file = video.uploaded_file.path

        if not os.path.exists(input_file):
            logger.error(f"Input file does not exist: {input_file}")
            video.status = 'failed'
            video.save()
            return

        hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))
        os.makedirs(hls_output_dir, exist_ok=True)

        key_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys')
        os.makedirs(key_dir, exist_ok=True)

        key_file = os.path.join(key_dir, f"{video.id}.key")
        key_uri = f"/media/videos/hls/{video.id}.key"
        key_info_file = os.path.join(key_dir, f"{video.id}.keyinfo")

        with open(key_file, 'wb') as f:
            f.write(os.urandom(16))

        with open(key_info_file, 'w') as f:
            f.write(f"{key_uri}\n")
            f.write(f"{key_file}\n")
            f.write("\n")

        renditions = [
            {'name': '240p', 'resolution': '426x240', 'bitrate': '400k', 'bandwidth': '500000'},
            {'name': '360p', 'resolution': '640x360', 'bitrate': '800k', 'bandwidth': '1000000'},
            {'name': '480p', 'resolution': '854x480', 'bitrate': '1400k', 'bandwidth': '1600000'},
            {'name': '720p', 'resolution': '1280x720', 'bitrate': '2800k', 'bandwidth': '3000000'},
        ]

        master_playlist = '#EXTM3U\n#EXT-X-VERSION:3\n'

        for r in renditions:
            rendition_dir = os.path.join(hls_output_dir, r['name'])
            os.makedirs(rendition_dir, exist_ok=True)

            playlist_filename = os.path.join(rendition_dir, 'playlist.m3u8')

            cmd = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-vf', f"scale={r['resolution']}",
                '-c:a', 'aac', '-ar', '48000',
                '-c:v', 'h264', '-profile:v', 'main',
                '-crf', '20', '-sc_threshold', '0',
                '-g', '48', '-keyint_min', '48',
                '-b:v', r['bitrate'],
                '-maxrate', r['bitrate'],
                '-bufsize', '1200k',
                '-b:a', '128k',
                '-hls_time', '4',
                '-hls_playlist_type', 'vod',
                '-hls_segment_filename', os.path.join(rendition_dir, 'segment_%03d.ts'),
                '-hls_key_info_file', key_info_file,
                playlist_filename
            ]

            logger.info(f"🎬 Running FFmpeg for {r['name']}: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, timeout=300)
            except subprocess.CalledProcessError as e:
                logger.exception(f"❌ FFmpeg failed for {r['name']}: {e}")
                video.status = 'failed'
                video.save()
                return

            master_playlist += (
                f'#EXT-X-STREAM-INF:BANDWIDTH={r["bandwidth"]},RESOLUTION={r["resolution"]}\n'
                f'{r["name"]}/playlist.m3u8\n'
            )

        with open(os.path.join(hls_output_dir, 'master.m3u8'), 'w') as f:
            f.write(master_playlist)

        video.hls_output_dir = f"videos/hls/{video.id}"
        video.aes_key_path = f"videos/keys/{video.id}.key"
        video.status = 'ready'
        video.save()

        logger.info(f"✅ Done processing video: {video.id}")

    except Exception as e:
        logger.exception(f"❌ Video processing failed: {e}")
        if video is not None:
            video.status = 'failed'
            video.save()