from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.db.models import Value
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.accounts.models import Avatar
from taskForce.tasks.manager import TaskManager

User = get_user_model()


class Task(models.Model):
    TYPE_CHOICES = (
        ("groceries", "Groceries"),
        ("workout", "Workout"),
        ("chores", "Chores"),
        ("list", "List"),
    )

    name = models.CharField(
        _("name"),
        max_length=100,
    )

    assigned_to = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_('assigned to'),
    )

    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('user'),
    )

    is_done = models.BooleanField(
        default=False,
        verbose_name=_('is done'),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at')
    )

    type = models.CharField(
        max_length=20,
        verbose_name=_('type'),
        choices=TYPE_CHOICES,
        null=True,
        blank=True,
    )

    unit = models.ForeignKey(
        to='units.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_('unit'),
    )

    appointed_points = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('appointed points'),
        blank=True,
    )

    accomplished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('accomplished at'),
    )

    due_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('due date'),
    )

    objects = TaskManager()

    def complete(self, user):
        with transaction.atomic():
            claimed = (
                Task.objects
                .filter(pk=self.pk, is_done=False)
                .update(
                    is_done=True,
                    assigned_to=user,
                    accomplished_at=timezone.now(),
                )
            )
            if not claimed:
                return False

            Avatar.objects.filter(user=user).update(
                points=models.F("points") + self.appointed_points
            )
        return True

    def uncomplete(self):
        with transaction.atomic():
            reverted = (
                Task.objects
                .filter(pk=self.pk, is_done=True)
                .update(
                    is_done=False,
                    assigned_to=None,
                    accomplished_at=None,
                )
            )
            if not reverted:
                return False

            if self.assigned_to_id:
                Avatar.objects.filter(user_id=self.assigned_to_id).update(
                    points=Greatest(models.F("points") - self.appointed_points, Value(0))
                )
        return True

    class Meta:
        verbose_name = _('task')
        verbose_name_plural = _('tasks')
        ordering = ["is_done", "-created_at"]
