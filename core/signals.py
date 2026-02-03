from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .feature_flags import is_master_user
from .models import UserProfile, ClassSession
from .services.institution_sync import mirror_master_classes


User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=ClassSession)
def auto_mirror_classes_on_save(sender, instance, **kwargs):
    user = getattr(instance.course, "user", None)
    if not user or not is_master_user(user):
        return
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return
    if not profile.auto_sync_master_classes:
        return
    mirror_master_classes(user)


@receiver(post_delete, sender=ClassSession)
def auto_mirror_classes_on_delete(sender, instance, **kwargs):
    user = getattr(instance.course, "user", None)
    if not user or not is_master_user(user):
        return
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return
    if not profile.auto_sync_master_classes:
        return
    mirror_master_classes(user)
