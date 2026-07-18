from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


TaskUser = get_user_model()


class Message(models.Model):
    text = models.TextField(
        verbose_name=_('Text'),
    )

    title = models.CharField(
        verbose_name=_('Title'),
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )

    sender = models.ForeignKey(
        to=TaskUser,
        on_delete=models.SET_NULL,
        verbose_name=_('Sender'),
        related_name='sent_messages',
        null=True,
        blank=True,
    )

    recipients = models.ManyToManyField(
        to=TaskUser,
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


class MessageRead(models.Model):
    message = models.ForeignKey(
        to=Message,
        on_delete=models.CASCADE,
        verbose_name=_('Message'),
        related_name='reads',
    )

    user = models.ForeignKey(
        to=TaskUser,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
        related_name='read_messages',
    )

    read_at = models.DateTimeField(
        verbose_name=_('Read at'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _('Read message')
        verbose_name_plural = _('Read messages')
        unique_together = (('user', 'message'),)
        ordering = ('-read_at', )