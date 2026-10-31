from django.db import models
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.mixins import RecurringItem, CheckableItem, recurring_checkable_constraints
from taskForce.tasks.models.task_item import TaskItem


class GroceryItem(RecurringItem, CheckableItem, TaskItem):
    quantity = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("quantity"),
    )

    class Meta(TaskItem.Meta):
        constraints = recurring_checkable_constraints("groceryitem")

