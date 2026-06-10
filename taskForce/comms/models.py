from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


User = get_user_model()


class Message(models.Model):
    text = models.TextField(
        verbose_name=_('Text'),
    )

    sender = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        verbose_name=_('Sender'),
        related_name='sent_messages',
        null=True,
        blank=True,
    )

    recipients = models.ManyToManyField(
        to=User,
        verbose_name=_('Recipients'),
        related_name='received_messages',
    )

    unit = models.ForeignKey(
        to="units.Unit",
        on_delete=models.SET_NULL,
        verbose_name=_('Unit'),
        related_name='unit_messages',
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        verbose_name=_('Created at'),
        auto_now_add=True,
    )

    modified_at = models.DateTimeField(
        verbose_name=_('Modified at'),
        auto_now=True,
    )

    related_task = models.ForeignKey(
        to="tasks.Task",
        on_delete=models.SET_NULL,
        verbose_name=_('Related task'),
        related_name='task_messages',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ('-created_at', )

    def __str__(self):
        return f"{self.sender} - {self.created_at:%d-%m-%Y %H:%M}"

