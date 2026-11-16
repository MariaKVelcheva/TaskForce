from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.mixins import checkable_constraints, CheckableItem
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


class WorkoutItem(CheckableItem, TaskItem):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")
        SATURDAY = 5, _("Saturday")
        SUNDAY = 6, _("Sunday")

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="workout_items",
        verbose_name=_("exercise"),
    )
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        null=True,
        blank=True,
        verbose_name=_("weekday"),
    )
    reps = models.CharField(max_length=100, blank=True, verbose_name=_("reps"))
    duration = models.DurationField(null=True, blank=True, verbose_name=_("duration"))
    weight = models.CharField(max_length=100, blank=True, verbose_name=_("weight"))

    class Meta(TaskItem.Meta):
        constraints = [
            *checkable_constraints("workoutitem"),
            models.CheckConstraint(
                condition=Q(weekday__isnull=True) | Q(weekday__lte=6),
                name="workoutitem_weekday_range",
            ),
        ]

