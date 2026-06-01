from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Avatar(models.Model):
    user = models.OneToOneField(
        to=User,
        on_delete=models.CASCADE,
        related_name='avatar',
        verbose_name=_('User'),
    )

    species = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('Species'),
    )

    hair_color = models.CharField(
        null=True,
        blank=True,
        verbose_name=_('Hair Color'),
    )

    glasses = models.BooleanField(
        default=False,
        verbose_name=_('Glasses'),
    )

    attire = models.ManyToManyField(
        to='attires.Attire',
        null=True,
        blank=True,
        related_name='avatars',
        verbose_name=_('Attire'),
    )

    points = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Points'),
    )

    class Meta:
        verbose_name = _('Avatar')
        verbose_name_plural = _('Avatars')

