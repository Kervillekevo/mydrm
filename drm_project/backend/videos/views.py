# videos/views.py

import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django_q.tasks import async_task

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Video
from .serializers import VideoSerializer


@login_required
def serve_aes_key(request, video_id):
    key_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'keys', f"{video_id}.key")
    if os.path.exists(key_path):
        return FileResponse(open(key_path, 'rb'), content_type='application/octet-stream')
    else:
        raise Http404("Key not found")


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        video = serializer.save()
        # enqueue the background processing task
        async_task('videos.tasks.process_video_task', video.id)
