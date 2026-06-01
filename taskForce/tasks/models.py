from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.manager import TaskManager

User = get_user_model()


class Task(models.Model):
    TYPE_CHOICES = (
        ("groceries", "Groceries"),
        ("travel", "Travel"),
        ("work", "Work"),
        ("school", "School"),
        ("chores", "Chores"),
        ("sports", "Sports"),
    )

    name = models.CharField(
        _("name"),
        max_length=100,
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
        verbose_name=_('created at'),
    )

    type = models.CharField(
        max_length=20,
        verbose_name=_('type'),
        choices=TYPE_CHOICES,
        null=True,
        blank=True,
    )

    zone = models.ForeignKey(
        to='zones.Zone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_('zone'),
    )

    unit = models.ForeignKey(
        to='units.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_('unit'),
    )

    brand = models.CharField(
        max_length=200,
        verbose_name=_('brand'),
        null=True,
        blank=True,
    )

    appointed_points = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('appointed points'),
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

    alarm_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('alarm at'),
    )

    timer_duration = models.DurationField(
        null=True,
        blank=True,
        verbose_name=_('timer duration'),
    )

    timer_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('timer at'),
    )

    objects = TaskManager()

    class Meta:
        verbose_name = _('task')
        verbose_name_plural = _('tasks')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'unit', 'name', 'zone'],
                condition=models.Q(is_done=False),
                name='unique_active_task_per_user_unit_zone'
            )
        ]
