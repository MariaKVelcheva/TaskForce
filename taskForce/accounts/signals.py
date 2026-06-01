from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from taskForce.accounts.models import Avatar


@receiver(post_save, sender=User)
def create_avatar(sender, instance, created, **kwargs):
    if created:
        Avatar.objects.create(
            user=instance,
        )



