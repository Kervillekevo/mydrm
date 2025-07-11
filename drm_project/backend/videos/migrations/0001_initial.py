# Generated by Django 5.2.4 on 2025-07-09 14:32

import django.db.models.deletion
import uuid
import videos.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('uploaded_file', models.FileField(upload_to=videos.models.video_upload_path)),
                ('hls_output_dir', models.CharField(blank=True, max_length=500)),
                ('aes_key_path', models.CharField(blank=True, max_length=500)),
                ('status', models.CharField(choices=[('uploaded', 'Uploaded'), ('processing', 'Processing'), ('ready', 'Ready'), ('failed', 'Failed')], default='uploaded', max_length=20)),
                ('views', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='videos', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
