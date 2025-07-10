#No blocking http request
#Users can upload a video and get a processing status
#Django Q for task queing
# videos/tasks.py

from videos.utils import process_video

def process_video_task(video_id):
    process_video(video_id)
    print(f"✅ Video {video_id} processed by Django Q task.")
