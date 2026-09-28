from django.db import models

from taskForce.tasks.manager import ChoreItemManager
from taskForce.tasks.models import TaskItem


class ChoresItem(TaskItem):
    minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    room = models.CharField(
        max_length=100,
        blank=True,
    )

    frequency_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    last_done_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = ChoreItemManager