from django.db import models
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models.task_item import TaskItem


class GroceryItem(TaskItem):
    quantity = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("quantity")
    )

