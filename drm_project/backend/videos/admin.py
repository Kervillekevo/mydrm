# admin.py

from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'views', 'created_at')
    search_fields = ('title', 'owner__username',)
    readonly_fields = ('video_preview', 'stream_link')
    
    fieldsets = (
        ('Video Details', {
            'fields': ('owner', 'title', 'description', 'uploaded_file', 'video_preview')
        }),
        ('Processing & Output', {
            'fields': ('hls_output_dir', 'aes_key_path', 'status', 'stream_link')
        }),
        ('Analytics', {
            'fields': ('views',)
        }),
    )

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
