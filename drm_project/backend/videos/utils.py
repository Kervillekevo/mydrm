import os
import subprocess
import shutil
import logging
import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.utils import timezone
from django.conf import settings
from videos.models import Video

logger = logging.getLogger(__name__)


def _encode_secure_path(raw_path: str) -> str:
    return base64.urlsafe_b64encode(raw_path.encode()).decode()


def rebuild_master_playlist(video: Video):
    output_dir = os.path.join(settings.MEDIA_ROOT, video.hls_output_dir)
    master_path = os.path.join(output_dir, 'master.m3u8')

    rendition_map = {
        '240p': ('426x240', 500000),
        '360p': ('640x360', 1000000),
        '480p': ('854x480', 1600000),
        '720p': ('1280x720', 3000000),
    }

    lines = ['#EXTM3U', '#EXT-X-VERSION:3']

    for rendition, (resolution, bandwidth) in rendition_map.items():
        playlist_path = os.path.join(output_dir, rendition, 'playlist.m3u8')
        if os.path.exists(playlist_path):
            lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}')
            lines.append(f'{rendition}/playlist.m3u8')

    with open(master_path, 'w') as f:
        f.write('\n'.join(lines))


def encode_rendition(r, input_file, hls_output_dir, key_info_path, video_id):
    try:
        rendition_dir = os.path.join(hls_output_dir, r['name'])
        os.makedirs(rendition_dir, exist_ok=True)
        playlist_path = os.path.join(rendition_dir, 'playlist.m3u8')
        bufsize = str(int(int(r['bitrate'].replace('k', '')) * 2)) + 'k'

        cmd = [
            'ffmpeg', '-y',
            '-i', input_file,
            '-vf', f"scale={r['resolution']}",
            '-c:a', 'aac', '-ar', '48000', '-b:a', '128k',
            '-c:v', 'h264',
            '-preset', 'ultrafast',
            '-profile:v', 'main',
            '-crf', '25',
            '-sc_threshold', '0',
            '-g', '30', '-keyint_min', '30',
            '-b:v', r['bitrate'],
            '-maxrate', r['bitrate'],
            '-bufsize', bufsize,
            '-hls_time', '6',
            '-hls_playlist_type', 'vod',
            '-hls_segment_filename', os.path.join(rendition_dir, 'segment_%03d.ts'),
            '-hls_key_info_file', key_info_path,
            playlist_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

        if result.returncode != 0:
            logger.error(f"❌ FFmpeg failed for {r['name']}: {result.stderr[-500:]}")
            return False, r['name']

        logger.info(f"✅ {r['name']} completed")
        return True, r['name']

    except subprocess.TimeoutExpired:
        logger.error(f"❌ {r['name']} timed out")
    except Exception as e:
        logger.error(f"❌ {r['name']} error: {e}")
    return False, r['name']


def process_video(video_id):
    logger.info(f"🚀 Starting process_video for {video_id}")
    video = None

    try:
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            logger.warning(f"⚠ Skipping processing — video {video_id} no longer exists in DB.")
            return

        logger.info(f"📽 Found video: {video.title}")

        video.status = 'processing'
        video.save(update_fields=['status'])

        input_file = video.uploaded_file.path
        if not os.path.exists(input_file):
            logger.error(f"❌ File not found: {input_file}")
            video.status = 'failed'
            video.save(update_fields=['status'])
            return

        hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))
        os.makedirs(hls_output_dir, exist_ok=True)

        key_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys')
        os.makedirs(key_dir, exist_ok=True)

        key_filename = f"{video.id}.key"
        key_src_path = os.path.join(key_dir, key_filename)
        key_public_path = os.path.join(hls_output_dir, key_filename)
        hls_parent_key_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', key_filename)

        with open(key_src_path, 'wb') as f:
            f.write(os.urandom(16))

        shutil.copy2(key_src_path, key_public_path)
        shutil.copy2(key_src_path, hls_parent_key_path)

        secure_key_url = f"/media/videos/hls/{key_filename}"
        key_info_path = os.path.join(hls_output_dir, f"{video.id}.keyinfo")
        with open(key_info_path, 'w') as f:
            f.write(f"{secure_key_url}\n{key_src_path}\n\n")

        probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', input_file]
        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=20)
            info = json.loads(result.stdout)
            duration = float(info['format']['duration'])
        except:
            duration = 0

        renditions = [
            {'name': '240p', 'resolution': '426:240', 'bitrate': '400k', 'bandwidth': '500000'},
            {'name': '360p', 'resolution': '640:360', 'bitrate': '800k', 'bandwidth': '1000000'},
            {'name': '480p', 'resolution': '854:480', 'bitrate': '1400k', 'bandwidth': '1600000'},
            {'name': '720p', 'resolution': '1280:720', 'bitrate': '2800k', 'bandwidth': '3000000'},
        ]

        logger.info("🎯 PRIORITY: Processing 240p first for immediate playback...")
        priority_rendition = next(r for r in renditions if r['name'] == '240p')

        rendition_dir = os.path.join(hls_output_dir, '240p')
        os.makedirs(rendition_dir, exist_ok=True)
        playlist_path = os.path.join(rendition_dir, 'playlist.m3u8')

        cmd_240p = [
            'ffmpeg', '-y',
            '-i', input_file,
            '-vf', f"scale={priority_rendition['resolution']}",
            '-c:a', 'aac', '-ar', '48000', '-b:a', '96k',
            '-c:v', 'h264',
            '-preset', 'ultrafast',
            '-profile:v', 'baseline',
            '-crf', '28',
            '-sc_threshold', '0',
            '-g', '30', '-keyint_min', '30',
            '-b:v', priority_rendition['bitrate'],
            '-maxrate', priority_rendition['bitrate'],
            '-bufsize', '800k',
            '-hls_time', '4',
            '-hls_playlist_type', 'vod',
            '-hls_segment_filename', os.path.join(rendition_dir, 'segment_%03d.ts'),
            '-hls_key_info_file', key_info_path,
            playlist_path
        ]

        try:
            logger.info("🏃‍♂ Starting ultrafast 240p encoding...")
            result = subprocess.run(cmd_240p, capture_output=True, text=True, timeout=900)

            if result.returncode != 0:
                logger.error(f"❌ FFmpeg failed for 240p: {result.stderr[-500:]}")
                video.status = 'failed'
                video.save(update_fields=['status'])
                return

            logger.info("✅ 240p processing completed!")

            Video.objects.filter(id=video.id).update(
                hls_output_dir=f"videos/hls/{video.id}",
                aes_key_path=f"videos/keys/{key_filename}",
                status='partial_ready',
            )

        except subprocess.TimeoutExpired:
            logger.error("❌ 240p processing timed out")
            video.status = 'failed'
            video.save(update_fields=['status'])
            return
        except Exception as e:
            logger.error(f"❌ 240p processing error: {e}")
            video.status = 'failed'
            video.save(update_fields=['status'])
            return

        logger.info("🔄 Starting parallel background processing for 360p, 480p, 720p...")

        remaining_renditions = [r for r in renditions if r['name'] != '240p']

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(encode_rendition, r, input_file, hls_output_dir, key_info_path, video.id): r['name']
                for r in remaining_renditions
            }

            for future in as_completed(futures):
                success, name = future.result()
                if success:
                    logger.info(f"✅ {name} rendition finished")

        rebuild_master_playlist(video)
        video.status = 'ready'
        video.save(update_fields=['status'])

        if os.path.exists(key_info_path):
            os.remove(key_info_path)

        logger.info(f"🎉 Video {video.id} fully processed - all resolutions available!")

    except Exception as e:
        logger.exception(f"❌ Processing failed for {video_id}: {e}")
        if video:
            video.status = 'failed'
            video.save(update_fields=['status'])
        raise