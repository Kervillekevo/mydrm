from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


def user_profile_photo_path(instance, filename):
    return f"user_{instance.user.id}/{filename}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=40, null=True, blank=True)
    profile_photo = models.ImageField(upload_to=user_profile_photo_path, blank=True)
    def __str__(self):
        return f"{self.user.username}'s Profile"
# Create your models here.


    # ✅ Signal to auto-create Profile when User is created
@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()