from django.db import models
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.mixins import checkable_constraints, CheckableItem
from taskForce.tasks.models import TaskItem


class WorkoutItem(CheckableItem, TaskItem):
    reps = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("reps"),
    )
    duration = models.DurationField(
        null=True,
        blank=True,
        verbose_name=_("duration"),
    )
    weight = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("weight"),
    )

    class Meta(TaskItem.Meta):
        constraints = checkable_constraints("workoutitem")