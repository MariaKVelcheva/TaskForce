from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from taskForce.comms.managers import ConversationManager

TaskUser = get_user_model()


class Conversation(models.Model):
    unit = models.ForeignKey(
        to="units.Unit",
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name=_("Unit"),
    )

    task = models.ForeignKey(
        to="tasks.Task",
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
        verbose_name=_("Task"),
    )

    created_at = models.DateTimeField(auto_now_add=True,)

    objects = ConversationManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "task"],
                name="unique_task_conversation",
            ),
            models.UniqueConstraint(
                fields=["unit"],
                condition=models.Q(task__isnull=True),
                name="unique_general_conversation",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def title(self):
        return self.task.name if self.task else self.unit.name


class Message(models.Model):
    conversation = models.ForeignKey(
        to=Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Conversation"),
    )

    sender = models.ForeignKey(
        to=TaskUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
        verbose_name=_("Sender"),
    )

    text = models.TextField(verbose_name=_("Text"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class ConversationRead(models.Model):
    conversation = models.ForeignKey(
        to=Conversation,
        on_delete=models.CASCADE,
        related_name="reads",
    )

    user = models.ForeignKey(
        to=TaskUser,
        on_delete=models.CASCADE,
        related_name="conversation_reads",
    )

    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "conversation"],
                name="unique_conversation_read",
            )
        ]