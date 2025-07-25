import os
import subprocess
import uuid
import logging
import shutil
import time

from django.core.management.base import BaseCommand
from django.conf import settings
from videos.models import Video

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Processes a video into multiple HLS renditions with AES-128 encryption.'

    def add_arguments(self, parser):
        parser.add_argument('video_id', type=str, nargs='?', help='The ID of the video to process')
        parser.add_argument('--all', action='store_true', help='Process all videos')

    def handle(self, *args, **options):
        video_id = options['video_id']
        process_all = options['all']

        if video_id and process_all:
            self.stderr.write(self.style.ERROR("❌ Cannot specify both video_id and --all."))
            return

        if process_all:
            self.stdout.write(self.style.SUCCESS("🚀 Processing all videos"))
            videos = Video.objects.all()
        elif video_id:
            try:
                videos = [Video.objects.get(id=video_id)]
            except Video.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"❌ Video with ID {video_id} not found."))
                return
        else:
            self.stderr.write(self.style.ERROR("❌ Provide a video_id or use --all."))
            return

        for video in videos:
            self.stdout.write(self.style.SUCCESS(f"🔧 Processing: {video.title} (ID: {video.id})"))
            try:
                self._process_single_video(video)
            except Exception as e:
                logger.exception(f"❌ Failed to process video {video.id}: {e}")
                video.status = 'failed'
                video.save()

        self.stdout.write(self.style.SUCCESS("✅ Done processing all videos."))

    def _process_single_video(self, video):
        input_file = video.uploaded_file.path
        if not os.path.exists(input_file):
            logger.error(f"❌ Missing input file: {input_file}")
            video.status = 'failed'
            video.save()
            return

        hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))
        if os.path.exists(hls_output_dir):
            shutil.rmtree(hls_output_dir)
        os.makedirs(hls_output_dir, exist_ok=True)

        # === AES Key Generation ===
        regenerate_key = False
        if video.aes_key_path:
            key_filename_from_db = os.path.basename(video.aes_key_path)
            if key_filename_from_db:
                key_id_from_db = key_filename_from_db.replace(".key", "")
                temp_master_key_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys', f"{key_id_from_db}.key")
                if os.path.exists(temp_master_key_path):
                    key_id = key_id_from_db
                else:
                    regenerate_key = True
            else:
                regenerate_key = True
        else:
            regenerate_key = True

        if regenerate_key:
            key_id = str(uuid.uuid4())

        keys_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys')
        os.makedirs(keys_dir, exist_ok=True)
        master_key_path = os.path.join(keys_dir, f"{key_id}.key")

        if not os.path.exists(master_key_path):
            with open(master_key_path, 'wb') as f:
                f.write(os.urandom(16))
            logger.info(f"🔐 AES key generated at {master_key_path}")

        hls_key_path = os.path.join(hls_output_dir, f"{key_id}.key")
        shutil.copy(master_key_path, hls_key_path)

        # Public URI for playlists
        key_uri = f"/media/videos/hls/{video.id}/{key_id}.key"

        # === .keyinfo Fix ===
        key_info_path = os.path.join(hls_output_dir, f"{key_id}.keyinfo")
        with open(key_info_path, 'w') as f:
            f.write(f"{key_uri}\n")         # Public URI for playlist
            f.write(f"{master_key_path}\n") # LOCAL path for FFmpeg
            f.write("\n")                   # Blank line for dynamic IV

        logger.info(f"📝 .keyinfo written: {key_info_path}")
        with open(key_info_path) as f:
            logger.debug(f"keyinfo content:\n{f.read()}")

        time.sleep(0.2)

        renditions = [
            {'name': '240p', 'resolution': '426x240', 'bitrate': '400k', 'maxrate': '450k', 'bufsize': '900k', 'bandwidth': '500000'},
            {'name': '360p', 'resolution': '640x360', 'bitrate': '800k', 'maxrate': '900k', 'bufsize': '1800k', 'bandwidth': '1000000'},
            {'name': '480p', 'resolution': '854x480', 'bitrate': '1400k', 'maxrate': '1500k', 'bufsize': '3000k', 'bandwidth': '1600000'},
            {'name': '720p', 'resolution': '1280x720', 'bitrate': '2800k', 'maxrate': '3000k', 'bufsize': '6000k', 'bandwidth': '3000000'},
        ]

        master_playlist = '#EXTM3U\n#EXT-X-VERSION:3\n'

        for r in renditions:
            rendition_dir = os.path.join(hls_output_dir, r['name'])
            os.makedirs(rendition_dir, exist_ok=True)
            playlist_path = os.path.join(rendition_dir, 'playlist.m3u8')

            cmd = [
                'ffmpeg', '-y', '-i', input_file,
                '-vsync', '0', '-pix_fmt', 'yuv420p',
                '-vf', f"scale={r['resolution']}",
                '-c:v', 'libx264', '-profile:v', 'main',
                '-sc_threshold', '0', '-g', '120', '-keyint_min', '120',
                '-b:v', r['bitrate'], '-maxrate', r['maxrate'], '-bufsize', r['bufsize'],
                '-hls_time', '4', '-hls_playlist_type', 'vod',
                '-hls_segment_filename', os.path.join(rendition_dir, 'segment_%03d.ts'),
                '-hls_flags', 'independent_segments',
                '-hls_key_info_file', key_info_path,
                '-c:a', 'aac', '-strict', '-2', '-ar', '48000', '-b:a', '128k',
                playlist_path
            ]

            try:
                result = subprocess.run(cmd, check=True, timeout=300, capture_output=True, text=True)
                logger.info(f"✅ FFmpeg {r['name']} output:\n{result.stdout}")
                if result.stderr:
                    logger.warning(f"⚠️ FFmpeg stderr:\n{result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ FFmpeg failed for {r['name']}: {e.stderr}")
                raise

            master_playlist += f'#EXT-X-STREAM-INF:BANDWIDTH={r["bandwidth"]},RESOLUTION={r["resolution"]}\n{r["name"]}/playlist.m3u8\n'

        master_path = os.path.join(hls_output_dir, 'master.m3u8')
        with open(master_path, 'w') as f:
            f.write(master_playlist)

        # Update model
        video.hls_output_dir = f"videos/hls/{video.id}"
        video.aes_key_path = f"videos/hls/{video.id}/{key_id}.key"
        video.status = 'ready'
        video.save()

        logger.info(f"📦 master.m3u8 saved: {master_path}")
        logger.info(f"🗝️ AES key copied: {hls_key_path}")
        logger.info(f"✅ Finished processing video {video.id}")

        os.remove(key_info_path)
