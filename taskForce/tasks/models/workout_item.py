from django.db import models

from taskForce.tasks.models import TaskItem


class WorkoutItem(TaskItem):
    reps = models.CharField(
        max_length=100,
        blank=True,
    )

    duration = models.DurationField(
        null=True,
        blank=True,
    )

    weight = models.CharField(
        max_length=100,
        blank=True,
    )