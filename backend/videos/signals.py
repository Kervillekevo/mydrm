# videos/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task
from .models import Video


@receiver(post_save, sender=Video)
def process_video_signal(sender, instance, created, **kwargs):
    """
    Automatically queue HLS processing whenever a video is uploaded,
    from either API or Django admin.
    """
    # Avoid reprocessing already processed videos
    if instance.status in ["processed", "processing"]:
        return

    # Process if file exists and it's a new upload
    if instance.uploaded_file:
        instance.status = "processing"
        instance.save(update_fields=["status"])

        # Correct reference to your actual function
        async_task("videos.utils.process_video", instance.id)
