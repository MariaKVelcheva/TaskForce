from django.db import models
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.manager import TaskItemManager
from taskForce.tasks.models import Task


class TaskItem(models.Model):
    task = models.ForeignKey(
        to=Task,
        on_delete=models.CASCADE,
        verbose_name=_("task"),
        related_name="%(class)s",
    )

    name = models.CharField(
        max_length=50,
        verbose_name=_("name"),
    )

    position = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("position"),
    )

    objects = TaskItemManager()

    class Meta:
        abstract = True
        ordering = ["position", "pk"]

    def save(self, *args, **kwargs):
        if not self.pk:
            last = self.__class__.objects.filter(task=self.task).order_by("-position").first()
            self.position = (last.position + 1) if last else 0
        super().save(*args, **kwargs)