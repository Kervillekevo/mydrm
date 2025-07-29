import uuid
import os
import base64
from django.db import models
from django.conf import settings
from django.urls import reverse

def video_upload_path(instance, filename):
    return f"videos/original/{instance.id}/{filename}"

class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='videos',
        null=True,
        blank=True
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    uploaded_file = models.FileField(upload_to=video_upload_path)

    hls_output_dir = models.CharField(max_length=500, blank=True)
    aes_key_path = models.CharField(max_length=500, blank=True)

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')

    views = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.id})"

    def hls_master_playlist_url(self):
        raw_url = reverse('serve_master_playlist', kwargs={'video_id': self.id})
        encoded = base64.urlsafe_b64encode(raw_url.encode()).decode()
        return f"/secure/hls/{encoded}"

    def aes_key_url(self):
        if self.aes_key_path:
            raw_url = reverse('serve_aes_key', kwargs={'video_id': self.id})
            encoded = base64.urlsafe_b64encode(raw_url.encode()).decode()
            return f"/secure/key/{encoded}"
        return ""

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
