from django.contrib import admin
from.models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'views', 'created_at')
    search_fields = ('title',)

# Register your models here.
