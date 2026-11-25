from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.mixins import checkable_constraints, CheckableItem, WeeklyItem, weekly_checkable_constraints
from taskForce.tasks.models import TaskItem


User = get_user_model()


class Exercise(models.Model):
    class Category(models.TextChoices):
        STRENGTH = "strength", _("Strength")
        CARDIO = "cardio", _("Cardio")
        MOBILITY = "mobility", _("Mobility")
        OTHER = "other", _("Other")

    name = models.CharField(max_length=50, verbose_name=_("name"))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name=_("category"),
    )
    owner = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exercises",
        verbose_name=_("owner"),
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "owner",
                name="unique_exercise_name_per_owner",
            ),
            models.UniqueConstraint(
                Lower("name"),
                condition=Q(owner__isnull=True),
                name="unique_shared_exercise_name",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_shared(self):
        return self.owner_id is None


class WorkoutItem(WeeklyItem, CheckableItem, TaskItem):
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        related_name="workout_items",
        verbose_name=_("exercise"),
    )
    reps = models.CharField(max_length=100, blank=True, verbose_name=_("reps"))
    duration = models.DurationField(null=True, blank=True, verbose_name=_("duration"))
    weight = models.CharField(max_length=100, blank=True, verbose_name=_("weight"))

    @property
    def minutes(self):
        return int(self.duration.total_seconds() // 60) if self.duration else None

    class Meta(TaskItem.Meta):
        constraints = weekly_checkable_constraints("workoutitem")


