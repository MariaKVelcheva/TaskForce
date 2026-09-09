from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from taskForce.accounts.models import Avatar


TaskUser = get_user_model()


@receiver(post_save, sender=TaskUser)
def create_avatar(sender, instance, created, **kwargs):
    if created:
        Avatar.objects.get_or_create(
            user=instance,
        )



