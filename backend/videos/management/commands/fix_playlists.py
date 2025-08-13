from django.core.management.base import BaseCommand
from videos.models import Video
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Fix HLS playlist key URIs to use correct <key_id>.key paths'

    def handle(self, *args, **options):
        videos = Video.objects.all()

        for video in videos:
            if not video.aes_key_path:
                self.stdout.write(self.style.WARNING(f"⚠️  Skipping video {video.id} (no aes_key_path)"))
                continue

            video_folder = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))

            key_filename = os.path.basename(video.aes_key_path)  # e.g. a3e82e1e-fef3-4248-8e58-a6cfc3caff96.key
            key_id = os.path.splitext(key_filename)[0]  # Remove .key extension to get just the UUID
            
            # FIXED: Generate URI that matches your URL pattern
            # Your URL pattern: 'media/videos/hls/<uuid:video_id>/<uuid:key_id>.key'
            key_uri = f"/media/videos/hls/{video.id}/{key_id}.key"

            for quality in ['240p', '360p', '480p', '720p']:
                playlist_path = os.path.join(video_folder, quality, 'playlist.m3u8')

                if not os.path.exists(playlist_path):
                    self.stdout.write(self.style.WARNING(f'⚠️  Not found: {playlist_path}'))
                    continue

                with open(playlist_path, 'r') as f:
                    content = f.read()

                new_lines = []
                key_fixed = False

                for line in content.splitlines():
                    if line.startswith('#EXT-X-KEY'):
                        new_line = (
                            f'#EXT-X-KEY:METHOD=AES-128,'
                            f'URI="{key_uri}",'
                            f'IV=0x00000000000000000000000000000000'
                        )
                        new_lines.append(new_line)
                        key_fixed = True
                        self.stdout.write(self.style.SUCCESS(f'🔑 Fixed key URI: {key_uri}'))
                    else:
                        new_lines.append(line)

                if key_fixed:
                    with open(playlist_path, 'w') as f:
                        f.write('\n'.join(new_lines))
                    self.stdout.write(self.style.SUCCESS(f'✅ Fixed key URI in: {playlist_path}'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  No key URI to fix in: {playlist_path}'))

        self.stdout.write(self.style.SUCCESS(f'🎬 Processed {videos.count()} videos'))