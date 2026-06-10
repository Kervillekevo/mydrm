from rest_framework import serializers
from videos.models import Video

class VideoSerializer(serializers.ModelSerializer):
    hls_url = serializers.SerializerMethodField()
    key_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'description',
            'uploaded_file',
            'status',
            'hls_url',
            'key_url',
        ]

    def get_hls_url(self, obj):
        if obj.status in ['partial_ready', 'ready']:
            return f"/videos/media/{obj.id}/manifest"
        return None

    def get_key_url(self, obj):
        if obj.status in ['partial_ready', 'ready']:
            return f"/videos/media/{obj.id}/key"
        return None