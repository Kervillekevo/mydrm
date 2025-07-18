# videos/management/commands/process_video.py

import os
import subprocess
import uuid
import logging
import shutil # Import shutil for potential cleanup

from django.core.management.base import BaseCommand
from django.conf import settings
from videos.models import Video

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Processes a video into multiple HLS renditions with AES-128 encryption. Can process a single video by ID or all videos.'

    def add_arguments(self, parser):
        # Make video_id argument optional with nargs='?'
        parser.add_argument('video_id', type=str, nargs='?',
                            help='The ID of the video to process (optional)')
        # Add the --all flag
        parser.add_argument('--all', action='store_true',
                            help='Process all videos in the database')

    def handle(self, *args, **options):
        video_id = options['video_id']
        process_all = options['all']

        if video_id and process_all:
            self.stderr.write(self.style.ERROR("Error: Cannot specify both a video_id and --all."))
            return

        if process_all:
            self.stdout.write(self.style.SUCCESS("🚀 Starting to process ALL videos."))
            videos_to_process = Video.objects.all()
        elif video_id:
            try:
                videos_to_process = [Video.objects.get(id=video_id)]
                self.stdout.write(self.style.SUCCESS(f"🚀 Starting to process single video: {video_id}"))
            except Video.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Error: Video with ID {video_id} not found."))
                return
        else:
            self.stderr.write(self.style.ERROR("Error: Please provide a video_id or use the --all flag."))
            return

        for video in videos_to_process:
            self.stdout.write(self.style.SUCCESS(f"Processing video: {video.title} (ID: {video.id})"))
            try:
                self._process_single_video(video) 
            except Exception as e:
                logger.exception(f"❌ Failed to process video {video.id}: {e}")
                self.stderr.write(self.style.ERROR(f"❌ Failed to process video {video.id}: {e}"))
                video.status = 'failed'
                video.save()

        self.stdout.write(self.style.SUCCESS("✅ Finished processing videos."))


    # --- FINAL, CORRECTED _process_single_video function ---
    def _process_single_video(self, video):
        input_file = video.uploaded_file.path

        if not os.path.exists(input_file):
            logger.error(f"Input file does not exist for video {video.id}: {input_file}")
            video.status = 'failed'
            video.save()
            return

        hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))

        # --- Clean up existing HLS and key files for this video ---
        if os.path.exists(hls_output_dir):
            shutil.rmtree(hls_output_dir)
            logger.info(f"Cleaned up old HLS directory: {hls_output_dir}")

        # Re-create HLS output directory
        os.makedirs(hls_output_dir, exist_ok=True)

        # 🔐 Store key file directly in HLS output dir
        # This is the corrected relative path for the key URI
        key_uri = f"../{video.id}.key"
        key_file = os.path.join(hls_output_dir, f"{video.id}.key")
        key_info_file = os.path.join(hls_output_dir, f"{video.id}.keyinfo")

        if os.path.exists(key_file):
            os.remove(key_file)
            logger.info(f"Cleaned up old key file: {key_file}")
        if os.path.exists(key_info_file):
            os.remove(key_info_file)
            logger.info(f"Cleaned up old key info file: {key_info_file}")

        with open(key_file, 'wb') as f:
            f.write(os.urandom(16))  # AES-128 => 16 bytes

        with open(key_info_file, 'w') as f:
            f.write(f"{key_uri}\n")
            f.write(f"{key_file}\n")
            f.write("\n")  # Let FFmpeg generate IV

        renditions = [
            {'name': '240p', 'resolution': '426x240', 'bitrate': '400k', 'max_bitrate': '450k', 'bufsize': '900k', 'bandwidth': '500000'},
            {'name': '360p', 'resolution': '640x360', 'bitrate': '800k', 'max_bitrate': '900k', 'bufsize': '1800k', 'bandwidth': '1000000'},
            {'name': '480p', 'resolution': '854x480', 'bitrate': '1400k', 'max_bitrate': '1500k', 'bufsize': '3000k', 'bandwidth': '1600000'},
            {'name': '720p', 'resolution': '1280x720', 'bitrate': '2800k', 'max_bitrate': '3000k', 'bufsize': '6000k', 'bandwidth': '3000000'},
        ]

        master_playlist = '#EXTM3U\n#EXT-X-VERSION:3\n'

        for r in renditions:
            rendition_dir = os.path.join(hls_output_dir, r['name'])
            os.makedirs(rendition_dir, exist_ok=True)

            playlist_filename = os.path.join(rendition_dir, 'playlist.m3u8')

            cmd = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-vsync', '0',
                '-pix_fmt', 'yuv420p',
                '-vf', f"scale={r['resolution']}",
                '-c:v', 'libx264',
                '-profile:v', 'main',
                '-sc_threshold', '0',
                '-g', '120',
                '-keyint_min', '120',
                '-b:v', r['bitrate'],
                '-maxrate', r['max_bitrate'],
                '-bufsize', r['bufsize'],
                '-hls_time', '4',
                '-hls_playlist_type', 'vod',
                '-hls_segment_filename', os.path.join(rendition_dir, 'segment_%03d.ts'),
                '-hls_key_info_file', key_info_file,
                '-hls_flags', 'independent_segments',
                '-c:a', 'aac',
                '-strict', '-2',
                '-ar', '48000',
                '-b:a', '128k',
                playlist_filename
            ]
            
            logger.info(f"🎬 Running FFmpeg for {r['name']} (Video: {video.id}): {' '.join(cmd)}")
            try:
                process = subprocess.run(cmd, check=True, timeout=300, capture_output=True, text=True)
                logger.info(f"FFmpeg stdout: {process.stdout}")
                if process.stderr:
                    logger.warning(f"FFmpeg stderr: {process.stderr}")
            except subprocess.CalledProcessError as e:
                logger.exception(f"❌ FFmpeg failed for {r['name']} (Video: {video.id}). Command: {' '.join(e.cmd)}. Return Code: {e.returncode}. STDOUT: {e.stdout}. STDERR: {e.stderr}")
                raise

            # This is the corrected line without the CODECS attribute
            master_playlist += (
                f'#EXT-X-STREAM-INF:BANDWIDTH={r["bandwidth"]},RESOLUTION={r["resolution"]}\n'
                f'{r["name"]}/playlist.m3u8\n'
            )

        master_playlist_path = os.path.join(hls_output_dir, 'master.m3u8')
        with open(master_playlist_path, 'w') as f:
            f.write(master_playlist)

        video.hls_output_dir = f"videos/hls/{video.id}"
        video.aes_key_path = f"videos/hls/{video.id}.key"
        video.status = 'ready'
        video.save()

        logger.info(f"✅ Successfully processed video: {video.id}")