from datetime import timedelta

from django.db import models
from django.db.models import F
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import TaskItem
from taskForce.tasks.mixins import (
    CheckableItem,
    RecurringItem,
    recurring_checkable_constraints,
)


class Room(models.Model):
    """A room of a chore rota (the Barracks). Duties with no room belong to General."""

    task = models.ForeignKey(
        to="tasks.Task",
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name=_("chore rota"),
    )
    name = models.CharField(
        max_length=40,
        verbose_name=_("name"),
    )
    position = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("position"),
    )

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(
                F("task"),
                Lower("name"),
                name="room_unique_name_per_task",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            last = Room.objects.filter(task_id=self.task_id).order_by("-position").first()
            self.position = (last.position + 1) if last else 0
        super().save(*args, **kwargs)


class ChoreItem(RecurringItem, CheckableItem, TaskItem):
    minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("minutes"),
    )

    # NULL = General. Deleting a room moves its duties there instead of deleting them.
    room = models.ForeignKey(
        to="tasks.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chores",
        verbose_name=_("room"),
    )

    @property
    def next_due_at(self):
        if self.frequency_days is None or self.last_done_at is None:
            return None
        return self.last_done_at + timedelta(days=self.frequency_days)

    class Meta(TaskItem.Meta):
        constraints = recurring_checkable_constraints("choreitem")

