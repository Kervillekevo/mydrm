# videos/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from .models import Video

@receiver(post_save, sender=Video)
def process_video_signal(sender, instance, created, **kwargs):
    if created and instance.uploaded_file:
        instance.status = 'processing'
        instance.save(update_fields=['status'])
        async_task('videos.tasks.process_video', instance.id)
