from django.db import models
from django.utils.translation import gettext_lazy as _

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

    is_done = models.BooleanField(
        default=False,
    )

    position = models.PositiveSmallIntegerField(
        default=0,
    )

    class Meta:
        abstract = True
        ordering = ["position", "pk"]

    def save(self, *args, **kwargs):
        last = self.__class__.objects.filter(task=self.task).order_by("-position").first()
        if last:
            self.position = last.position + 1
        else:
            self.position = 0
        super().save(*args, **kwargs)
