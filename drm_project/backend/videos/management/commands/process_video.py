# videos/management/commands/process_video.py

import os
import subprocess
import uuid

from django.core.management.base import BaseCommand
from django.conf import settings
from videos.models import Video

class Command(BaseCommand):
    help = 'Processes a video into multiple HLS renditions with AES-128 encryption'

    def add_arguments(self, parser):
        parser.add_argument('video_id', type=str)

    def handle(self, *args, **options):
        video_id = options['video_id']
        video = Video.objects.get(id=video_id)

        input_file = video.uploaded_file.path

        # Create folders
        hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))
        os.makedirs(hls_output_dir, exist_ok=True)

        key_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys')
        os.makedirs(key_dir, exist_ok=True)

        # AES key & keyinfo
        key_file = os.path.join(key_dir, f"{video.id}.key")
        key_uri = f"/videos/key/{video.id}.key"
        key_info_file = os.path.join(key_dir, f"{video.id}.keyinfo")

        with open(key_file, 'wb') as f:
            f.write(os.urandom(16))  # AES-128 => 16 bytes

        with open(key_info_file, 'w') as f:
            f.write(f"{key_uri}\n")
            f.write(f"{key_file}\n")
            f.write(f"\n")  # Let FFmpeg generate IV

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
                '-c:a', 'aac',
                '-ar', '48000',
                '-c:v', 'h264',
                '-profile:v', 'main',
                '-crf', '20',
                '-sc_threshold', '0',
                '-g', '48',
                '-keyint_min', '48',
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

            subprocess.run(cmd, check=True)

            master_playlist += (
                f'#EXT-X-STREAM-INF:BANDWIDTH={r["bandwidth"]},RESOLUTION={r["resolution"]}\n'
                f'{r["name"]}/playlist.m3u8\n'
            )

        # Write master.m3u8
        master_playlist_path = os.path.join(hls_output_dir, 'master.m3u8')
        with open(master_playlist_path, 'w') as f:
            f.write(master_playlist)

        # Update Video model
        video.hls_output_dir = f"videos/hls/{video.id}"
        video.aes_key_path = f"videos/keys/{video.id}.key"
        video.status = 'ready'
        video.save()

        self.stdout.write(self.style.SUCCESS(f"✅ Processed renditions for: {video.id}"))
