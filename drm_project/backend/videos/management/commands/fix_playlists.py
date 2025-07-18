from django.core.management.base import BaseCommand
from videos.models import Video
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Fix HLS playlist key URIs to match the Django API'

    def handle(self, *args, **options):
        videos = Video.objects.all()

        for video in videos:
            video_folder = os.path.join(
                settings.MEDIA_ROOT,
                'videos', 'hls',
                str(video.id)
            )

            for quality in ['240p', '360p', '480p', '720p']:
                playlist_path = os.path.join(video_folder, quality, 'playlist.m3u8')

                if not os.path.exists(playlist_path):
                    self.stdout.write(self.style.WARNING(f'⚠️  Not found: {playlist_path}'))
                    continue

                with open(playlist_path, 'r') as f:
                    content = f.read()

                # ✅ Key URI should be /media/videos/hls/<video_id>/<video_id>.key
                key_filename = f"{video.id}.key"
                key_uri = f"/media/videos/hls/{video.id}/{key_filename}"

                new_lines = []
                for line in content.splitlines():
                    if line.startswith('#EXT-X-KEY'):
                        new_line = (
                            f'#EXT-X-KEY:METHOD=AES-128,'
                            f'URI="{key_uri}",'
                            f'IV=0x00000000000000000000000000000000'
                        )
                        new_lines.append(new_line)
                    else:
                        new_lines.append(line)

                new_content = '\n'.join(new_lines)

                with open(playlist_path, 'w') as f:
                    f.write(new_content)

                self.stdout.write(self.style.SUCCESS(f'✅ Fixed: {playlist_path}'))
