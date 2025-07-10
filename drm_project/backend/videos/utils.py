# videos/utils.py

import os
import subprocess
import uuid

from django.conf import settings
from videos.models import Video

def process_video(video_id):
    video = Video.objects.get(id=video_id)

    input_file = video.uploaded_file.path

    hls_output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'hls', str(video.id))
    os.makedirs(hls_output_dir, exist_ok=True)

    key_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys')
    os.makedirs(key_dir, exist_ok=True)

    # AES key
    key_file = os.path.join(key_dir, f"{video.id}.key")
    key_uri = f"/videos/key/{video.id}.key"
    key_info_file = os.path.join(key_dir, f"{video.id}.keyinfo")

    with open(key_file, 'wb') as f:
        f.write(os.urandom(16))  # AES-128

    with open(key_info_file, 'w') as f:
        f.write(f"{key_uri}\n")
        f.write(f"{key_file}\n")
        f.write(f"\n")

    renditions = [
        {'name': '240p', 'resolution': '426x240', 'bitrate': '400k'},
        {'name': '360p', 'resolution': '640x360', 'bitrate': '800k'},
        {'name': '480p', 'resolution': '854x480', 'bitrate': '1400k'},
        {'name': '720p', 'resolution': '1280x720', 'bitrate': '2800k'},
    ]

    variant_playlists = []

    for r in renditions:
        playlist_name = f"{r['name']}.m3u8"
        output_playlist = os.path.join(hls_output_dir, playlist_name)

        cmd = [
            'ffmpeg', '-y',
            '-i', input_file,
            '-vf', f"scale={r['resolution']}",
            '-c:a', 'aac', '-ar', '48000', '-c:v', 'h264', '-profile:v', 'main',
            '-crf', '20', '-sc_threshold', '0',
            '-g', '48', '-keyint_min', '48',
            '-b:v', r['bitrate'],
            '-maxrate', f"{int(int(r['bitrate'][:-1]) * 1.07)}k",
            '-bufsize', f"{int(int(r['bitrate'][:-1]) * 1.5)}k",
            '-hls_time', '4',
            '-hls_playlist_type', 'vod',
            '-hls_segment_filename', os.path.join(hls_output_dir, f"{r['name']}_%03d.ts"),
            '-hls_key_info_file', key_info_file,
            output_playlist
        ]

        subprocess.run(cmd, check=True)

        variant_playlists.append({
            'resolution': r['resolution'],
            'bandwidth': r['bitrate'].replace('k', '000'),
            'playlist': playlist_name
        })

    # Build master playlist
    master_playlist = "#EXTM3U\n"

    for v in variant_playlists:
        master_playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={v['bandwidth']},RESOLUTION={v['resolution']}\n"
        master_playlist += f"{v['playlist']}\n"

    with open(os.path.join(hls_output_dir, 'master.m3u8'), 'w') as f:
        f.write(master_playlist)

    video.hls_output_dir = f"videos/hls/{video.id}"
    video.aes_key_path = f"videos/keys/{video.id}.key"
    video.status = 'ready'
    video.save()

    return video
