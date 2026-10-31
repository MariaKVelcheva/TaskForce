from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from taskForce.tasks.models import TaskItem
from taskForce.tasks.mixins import (
    CheckableItem,
    RecurringItem,
    recurring_checkable_constraints,
)


class ChoreItem(RecurringItem, CheckableItem, TaskItem):
    class Room(models.TextChoices):
        GENERAL = "", _("General")
        KITCHEN = "kitchen", _("Kitchen")
        BATHROOM = "bathroom", _("Bathroom")
        BEDROOM = "bedroom", _("Bedroom")
        LIVING = "living", _("Living room")
        OUTDOOR = "outdoor", _("Outdoor")

    minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("minutes"),
    )

    room = models.CharField(
        max_length=20,
        blank=True,
        choices=Room.choices,
        default=Room.GENERAL,
        verbose_name=_("room"),
    )

    class Meta(TaskItem.Meta):
        constraints = recurring_checkable_constraints("choreitem")
