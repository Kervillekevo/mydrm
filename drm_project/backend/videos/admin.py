from django.contrib import admin
from django.utils.safestring import mark_safe
from django_q.tasks import async_task  # ✅ Required for background processing

from .models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'views', 'created_at', 'aes_key_link')
    search_fields = ('title', 'owner__username',)
    readonly_fields = ('video_preview', 'stream_link', 'aes_key_link')

    fieldsets = (
        ('Video Details', {
            'fields': ('owner', 'title', 'description', 'uploaded_file', 'video_preview')
        }),
        ('Processing & Output', {
            'fields': ('hls_output_dir', 'aes_key_path', 'status', 'stream_link', 'aes_key_link')
        }),
        ('Analytics', {
            'fields': ('views',)
        }),
    )

    def save_model(self, request, obj, form, change):
        # Save the Video object normally
        super().save_model(request, obj, form, change)

        # Only queue for processing if status is still uploaded (not ready yet)
        if obj.status == 'uploaded' and obj.uploaded_file:
            async_task('videos.tasks.process_video_task', obj.id)
            self.message_user(request, f"✅ Video {obj.id} queued for processing!")

    def video_preview(self, obj):
        if obj.uploaded_file:
            return mark_safe(
                f'<video width="640" height="360" controls style="border:1px solid #ccc">'
                f'<source src="{obj.uploaded_file.url}" type="video/mp4">'
                f'Your browser does not support the video tag.'
                f'</video>'
            )
        return "No video uploaded yet."

    video_preview.short_description = "Preview"

    def stream_link(self, obj):
        if obj.status == 'ready':
            url = obj.hls_master_playlist_url()
            return mark_safe(f'<a href="{url}" target="_blank">{url}</a>')
        return "Not ready yet."

    stream_link.short_description = "Streaming Link"

    def aes_key_link(self, obj):
        if obj.status == 'ready':
            url = obj.aes_key_url()
            return mark_safe(f'<a href="{url}" target="_blank">{url}</a>')
        return "Not ready yet."

    aes_key_link.short_description = "AES Key Link"
