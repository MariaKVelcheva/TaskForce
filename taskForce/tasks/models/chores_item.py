from django.db import models

from taskForce.tasks.manager import ChoreItemManager
from taskForce.tasks.models import TaskItem


class ChoreItem(TaskItem):
    ROOM_CHOICES = (
        ("", "Section"),
        ("kitchen", "Kitchen"),
        ("bathroom", "Bathroom"),
        ("bedroom", "Bedroom"),
        ("living", "Living room"),
        ("outdoor", "Outdoor"),
    )

    minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    room = models.CharField(
        max_length=100,
        blank=True,
        choices=ROOM_CHOICES,
    )

    frequency_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    last_done_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = ChoreItemManager()

