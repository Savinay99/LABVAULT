"""Resources app signals: auto-generate in-app notifications on key actions."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Notification, Resource


def notify(recipient, verb, target_url="", notif_type=Notification.NOTIF_INFO, actor=None):
    """Create an in-app notification for a user."""
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        verb=verb,
        target_url=target_url,
        notif_type=notif_type,
    )


@receiver(post_save, sender=Resource)
def notify_on_resource_created(sender, instance, created, **kwargs):
    """Notify the uploader when a new resource is uploaded."""
    if not created:
        return
    notify(
        recipient=instance.uploaded_by,
        verb=f'Your resource "{instance.title}" was uploaded successfully.',
        target_url=reverse("resources:details", args=[instance.pk]),
        notif_type=Notification.NOTIF_SUCCESS,
        actor=instance.uploaded_by,
    )
    # Notify administrators that a new resource is available for review.
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for admin in User.objects.filter(role=User.ROLE_ADMIN).exclude(pk=instance.uploaded_by.pk):
        notify(
            recipient=admin,
            verb=f'New resource uploaded: "{instance.title}" by {instance.uploaded_by.get_full_name() or instance.uploaded_by.email}.',
            target_url=reverse("resources:details", args=[instance.pk]),
            notif_type=Notification.NOTIF_INFO,
            actor=instance.uploaded_by,
        )
