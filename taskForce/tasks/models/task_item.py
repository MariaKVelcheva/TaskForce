from django.db import models
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.manager import TaskItemManager
from taskForce.tasks.models import Task


class TaskItem(models.Model):
    task = models.ForeignKey(
        to=Task,
        on_delete=models.CASCADE,
        verbose_name=_('task'),
        related_name='%(class)s',
    )

    name = models.CharField(
        max_length=50,
        verbose_name=_('name'),
    )

    is_active = models.BooleanField(
        default=False,
    )

    position = models.PositiveSmallIntegerField(
        default=0,
    )

    objects = TaskItemManager()

    class Meta:
        abstract = True
        ordering = ["position", "pk"]

    def toggle(self):
        self.is_active = not self.is_active
        self.save(update_fields=['is_active'])

    def save(self, *args, **kwargs):
        if not self.pk:
            last = self.__class__.objects.filter(task=self.task).order_by("-position").first()
            self.position = (last.position + 1) if last else 0
        super().save(*args, **kwargs)
