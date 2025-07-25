import os
import subprocess
import uuid
import shutil
import logging

from django.conf import settings
from videos.models import Video

logger = logging.getLogger(__name__)

def process_video(video_id):
    logger.info(f"🚀 Starting process_video for {video_id}")
    video = None

    try:
        video = Video.objects.get(id=video_id)
        video.status = 'processing'
        video.save()

        input_file = video.uploaded_file.path
        if not os.path.exists(input_file):
            logger.error(f"❌ Input file does not exist: {input_file}")
            video.status = 'failed'
            video.save()
            return

        # === Paths Setup ===
        hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))
        os.makedirs(hls_output_dir, exist_ok=True)

        key_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys')
        os.makedirs(key_dir, exist_ok=True)

        # === AES Key Setup ===
        key_filename = f"{video.id}.key"  # Must match /media/videos/hls/<video_id>.key
        key_src_path = os.path.join(key_dir, key_filename)
        key_public_path = os.path.join(hls_output_dir, key_filename)

        key_uri = f"/media/videos/hls/{video.id}.key"  # Matches urls.py and serve_aes_key

        with open(key_src_path, 'wb') as f:
            f.write(os.urandom(16))

        shutil.copy(key_src_path, key_public_path)
        logger.info(f"🔑 Key copied to: {key_public_path}")

        key_info_path = os.path.join(hls_output_dir, f"{video.id}.keyinfo")
        with open(key_info_path, 'w') as f:
            f.write(f"{key_uri}\n")         # Public URL for ffmpeg
            f.write(f"{key_src_path}\n")    # Local file path
            f.write("\n")
        logger.info(f"📝 Key info file created: {key_info_path} with URI: {key_uri}")

        # === Renditions ===
        renditions = [
            {'name': '240p', 'resolution': '426x240', 'bitrate': '400k',  'bandwidth': '500000'},
            {'name': '360p', 'resolution': '640x360', 'bitrate': '800k',  'bandwidth': '1000000'},
            {'name': '480p', 'resolution': '854x480', 'bitrate': '1400k', 'bandwidth': '1600000'},
            {'name': '720p', 'resolution': '1280x720','bitrate': '2800k', 'bandwidth': '3000000'},
        ]

        generated_master_playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"

        for r in renditions:
            rendition_dir = os.path.join(hls_output_dir, r['name'])
            os.makedirs(rendition_dir, exist_ok=True)
            playlist_path = os.path.join(rendition_dir, 'playlist.m3u8')

            cmd = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-vf', f"scale={r['resolution']}",
                '-c:a', 'aac', '-ar', '48000', '-b:a', '128k',
                '-c:v', 'h264', '-profile:v', 'main',
                '-crf', '20',
                '-sc_threshold', '0',
                '-g', '48', '-keyint_min', '48',
                '-b:v', r['bitrate'],
                '-maxrate', r['bitrate'],
                '-bufsize', '1200k',
                '-hls_time', '4',
                '-hls_playlist_type', 'vod',
                '-hls_segment_filename', os.path.join(rendition_dir, 'segment_%03d.ts'),
                '-hls_key_info_file', key_info_path,
                playlist_path
            ]

            logger.info(f"🎬 Running FFmpeg for {r['name']}: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, timeout=300, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"❌ FFmpeg for {r['name']} failed with code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                raise Exception(f"FFmpeg failed for {r['name']} rendition")

            logger.info(f"✅ Successfully generated {r['name']} rendition.")

            # --- Fix AES key URI in playlist ---
            with open(playlist_path, 'r') as f:
                content = f.read()

            fixed_lines = []
            for line in content.splitlines():
                if line.startswith('#EXT-X-KEY'):
                    fixed_line = f'#EXT-X-KEY:METHOD=AES-128,URI="{key_uri}",IV=0x00000000000000000000000000000000'
                    fixed_lines.append(fixed_line)
                    logger.info(f"🔑 Fixed key URI in {r['name']} playlist: {key_uri}")
                else:
                    fixed_lines.append(line)

            with open(playlist_path, 'w') as f:
                f.write('\n'.join(fixed_lines))

            generated_master_playlist_content += (
                f'#EXT-X-STREAM-INF:BANDWIDTH={r["bandwidth"]},RESOLUTION={r["resolution"]}\n'
                f'{r["name"]}/playlist.m3u8\n'
            )

        # === Write Master Playlist ===
        master_playlist_path = os.path.join(hls_output_dir, 'master.m3u8')
        with open(master_playlist_path, 'w') as f:
            f.write(generated_master_playlist_content)
        logger.info(f"✅ Master playlist created: {master_playlist_path}")

        # === Save Video Model ===
        video.hls_output_dir = f"videos/hls/{video.id}"
        video.aes_key_path = f"videos/hls/{video.id}.key"  # Consistent with views/urls
        video.status = 'ready'
        video.save()
        logger.info(f"✅ Video saved with aes_key_path: {video.aes_key_path}")

        # === Cleanup ===
        os.remove(key_info_path)
        logger.info(f"✅ Finished processing video {video.id}")

    except Exception as e:
        logger.exception(f"❌ Failed to process video {video_id}: {e}")
        if video:
            video.status = 'failed'
            video.save()
