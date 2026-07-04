import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class Unit(models.Model):
    users = models.ManyToManyField(
        to=User,
        through='Membership',
        related_name='units',
        verbose_name=_('users'),
    )

    name = models.CharField(
        verbose_name=_('name'),
        max_length=55,
    )

    created_by = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_units',
        verbose_name=_('created by'),
    )

    invite_code = models.UUIDField(
        default=uuid.uuid4,
        verbose_name=_('invite code'),
        unique=True,
        editable=False,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('unit')
        verbose_name_plural = _('units')


class Membership(models.Model):
    ROLES = (
        ("commander", _("Commander")),
        ("operative", _("Operative")),
    )

    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        verbose_name=_('user'),
        related_name='memberships',
    )

    role = models.CharField(
        verbose_name=_('role'),
        choices=ROLES,
        max_length=55,
        default='operative',
    )

    unit = models.ForeignKey(
        to=Unit,
        on_delete=models.CASCADE,
        verbose_name=_('unit'),
        related_name='memberships',
    )

    def __str__(self):
        return f'{self.user}: {self.role} of {self.unit}'

    class Meta:
        verbose_name = _('membership')
        verbose_name_plural = _('memberships')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'unit'],
                name='unique_membership',
            )
        ]
