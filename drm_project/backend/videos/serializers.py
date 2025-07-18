# videos/serializers.py

from rest_framework import serializers
from videos.models import Video

class VideoSerializer(serializers.ModelSerializer):
    hls_url = serializers.SerializerMethodField()
    key_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id',
                  'title',
                  'description',
                  'uploaded_file',
                  'status',
                  'hls_output_dir',
                  'aes_key_path',
                  'hls_url',
                  'key_url'
                  ]

    def get_hls_url(self, obj):
        if obj.status == 'ready':
            # Use the model method for consistency
            return obj.hls_master_playlist_url()
        return None

    def get_key_url(self, obj):
        if obj.status == 'ready':
            # !!! THIS IS THE CRITICAL CHANGE !!!
            # Use the model method which now returns the correct URL
            return obj.aes_key_url()
        return None