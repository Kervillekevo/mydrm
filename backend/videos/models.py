import uuid
import os
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
        related_name="videos",
        null=True,
        blank=True
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    uploaded_file = models.FileField(upload_to=video_upload_path)

    # Stored as RELATIVE paths inside MEDIA_ROOT
    hls_output_dir = models.CharField(max_length=500, blank=True)
    aes_key_path = models.CharField(max_length=500, blank=True)

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("partial_ready", "Partially Ready"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")

    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # ==========================
    # UI HELPERS
    # ==========================

    def poster_url(self):
        poster_path = f"videos/thumbnails/{self.id}.jpg"
        abs_path = os.path.join(settings.MEDIA_ROOT, poster_path)

        if os.path.exists(abs_path):
            return settings.MEDIA_URL + poster_path

        return static("images/default-poster.jpg")

    def __str__(self):
        return f"{self.title} ({self.id})"

    # ==========================
    # STREAMING URLS (RAW)
    # ==========================

    def hls_master_playlist_url(self):
        """
        IMPORTANT:
        - No token here
        - No base64 here
        - Token is injected in views.py
        """
        return reverse(
            "serve_master_playlist",
            kwargs={"video_id": self.id}
        )

    def aes_key_url(self):
        """
        Used internally by FFmpeg / views.
        """
        if not self.aes_key_path:
            return ""
        return reverse(
            "serve_aes_key",
            kwargs={"video_id": self.id}
        )

    # ==========================
    # EMBED (REQUIRED)
    # ==========================

    def embed_code(self):
        base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000")
        embed_url = f"{base_url}{self.get_embed_url()}"
        return (
            f"<iframe "
            f"src='{embed_url}' "
            f"width='640' height='360' "
            f"frameborder='0' allowfullscreen>"
            f"</iframe>"
        )


    def get_embed_url(self):
        return reverse("video-embed", kwargs={"video_id": self.id})


    # ==========================
    # CLEAN DELETE (SAFE)
    # ==========================

    def delete(self, *args, **kwargs):
        """
        Deletes:
        - Original uploaded file folder
        - This video's HLS output folder
        - This video's AES key
        - DB row
        """

        # 1. Original upload folder
        if self.uploaded_file:
            try:
                original_dir = os.path.dirname(self.uploaded_file.path)
                if os.path.exists(original_dir):
                    shutil.rmtree(original_dir)
            except Exception as e:
                print(f"⚠ Failed to delete original files for {self.id}: {e}")

        # 2. HLS output folder (THIS VIDEO ONLY)
        if self.hls_output_dir:
            hls_dir = os.path.join(settings.MEDIA_ROOT, self.hls_output_dir)
            if os.path.exists(hls_dir):
                try:
                    shutil.rmtree(hls_dir)
                except Exception as e:
                    print(f"⚠ Failed to delete HLS for {self.id}: {e}")

        # 3. AES key (THIS VIDEO ONLY)
        if self.aes_key_path:
            key_path = os.path.join(settings.MEDIA_ROOT, self.aes_key_path)
            if os.path.exists(key_path):
                try:
                    os.remove(key_path)
                except Exception as e:
                    print(f"⚠ Failed to delete AES key for {self.id}: {e}")

        super().delete(*args, **kwargs)
