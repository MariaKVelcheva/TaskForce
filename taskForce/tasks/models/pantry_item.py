from django.db import models
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import TaskItem


class PantryItem(TaskItem):
    quantity = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("in stock"),
    )
    threshold = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("restock at"),
    )

    class Meta(TaskItem.Meta):
        pass

