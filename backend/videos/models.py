import uuid
import os
import base64
import shutil
from django.db import models
from django.conf import settings
from django.urls import reverse

from django.templatetags.static import static

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

    hls_output_dir = models.CharField(max_length=500, blank=True)  # relative path
    aes_key_path = models.CharField(max_length=500, blank=True)    # relative path

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('partial_ready', 'Partially Ready'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')

    views = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def poster_url(self):
        # If you have a real generated poster path, use that
        poster_path = f"videos/thumbnails/{self.id}.jpg"  
        abs_path = os.path.join(settings.MEDIA_ROOT, poster_path)

        if os.path.exists(abs_path):
            return settings.MEDIA_URL + poster_path
        
        # Fallback to a default static image
        return static("images/default-poster.jpg")

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

    def delete(self, *args, **kwargs):
        """
        Delete video files, HLS output (and all .key files in HLS tree), AES key, and original folder.
        """

        # 1. Delete original folder
        if self.uploaded_file:
            try:
                folder_path = os.path.dirname(self.uploaded_file.path)
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path)
            except Exception as e:
                print(f"⚠ Could not delete original folder for Video {self.id}: {e}")

        # 2. Delete HLS output folder for this video
        if self.hls_output_dir:
            hls_abs_path = os.path.join(settings.MEDIA_ROOT, self.hls_output_dir)
            if os.path.exists(hls_abs_path):
                try:
                    shutil.rmtree(hls_abs_path)
                except Exception as e:
                    print(f"⚠ Could not delete HLS folder for Video {self.id}: {e}")

        # 2b. Remove ALL .key files anywhere inside the global HLS folder
        hls_root_path = os.path.join(settings.MEDIA_ROOT, "videos", "hls")
        if os.path.exists(hls_root_path):
            for root, dirs, files in os.walk(hls_root_path):
                for file in files:
                    if file.endswith(".key"):
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception as e:
                            print(f"⚠ Could not delete leftover HLS key {file}: {e}")

        # 3. Delete AES key file in the separate keys folder
        if self.aes_key_path:
            aes_abs_path = os.path.join(settings.MEDIA_ROOT, self.aes_key_path)
            if os.path.exists(aes_abs_path):
                try:
                    os.remove(aes_abs_path)
                except Exception as e:
                    print(f"⚠ Could not delete AES key for Video {self.id}: {e}")

        super().delete(*args, **kwargs)

def embed_code(self):
    base_url = getattr(settings, "SITE_BASE_URL", "http://104.152.49.62")
    return f"<iframe src='{base_url}{self.get_embed_url()}' width='640' height='360' frameborder='0' allowfullscreen></iframe>"