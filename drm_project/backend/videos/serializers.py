# videos/serializers.py

from rest_framework import serializers
from videos.models import Video

class VideoSerializer(serializers.ModelSerializer):
    hls_url = serializers.SerializerMethodField()
    key_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'uploaded_file', 'status', 'hls_url', 'key_url']

    def get_hls_url(self, obj):
        if obj.status == 'ready':
            return f"/media/{obj.hls_output_dir}/master.m3u8"
        return None

    def get_key_url(self, obj):
        if obj.status == 'ready':
            return f"/videos/key/{obj.id}.key"
        return None
