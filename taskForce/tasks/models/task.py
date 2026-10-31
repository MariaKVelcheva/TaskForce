from django.contrib.auth.models import User
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.db.models import Value, F, Q
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.accounts.models import Avatar
from taskForce.tasks.manager import TaskManager


TaskUser = get_user_model()


class TaskType(models.TextChoices):
    ONEOFF = "oneoff", _("Special Op")
    GROCERIES = "groceries", _("Groceries")
    PANTRY = "pantry", _("Pantry")
    CHORES = "chores", _("Chores")
    WORKOUT = "workout", _("Workout")
    LIST = "list", _("List")


SINGLETON_TYPES = [
    TaskType.GROCERIES,
    TaskType.PANTRY,
    TaskType.CHORES,
    TaskType.WORKOUT,
]


class Task(models.Model):
    PRIORITY_CHOICES = (
        (1, "Critical"),
        (2, "High"),
        (3, "Routine"),
    )

    name = models.CharField(
        _("name"),
        max_length=100,
    )

    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY_CHOICES, default=3,
        verbose_name=_("priority"),
    )

    assigned_to = models.ForeignKey(
        to=TaskUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_('assigned to'),
    )

    user = models.ForeignKey(
        to=TaskUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks',
        verbose_name=_('user'),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('created at')
    )

    type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.ONEOFF,
        verbose_name=_("type"),
    )

    comment = models.TextField(
        blank=True,
        verbose_name=_('comment'),
    )

    unit = models.ForeignKey(
        to='units.Unit',
        on_delete=models.SET_NULL,
        null=True,
        related_name='tasks',
        verbose_name=_('unit'),
    )

    is_accomplished = models.BooleanField(
        default=False,
        verbose_name=_("accomplished"),
    )

    accomplished_by = models.ForeignKey(
        to=TaskUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("accomplished by"),
    )

    due_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('due date'),
    )

    is_active = models.BooleanField(default=True, verbose_name=_("is_active"),)

    objects = TaskManager()

    def accomplish(self, user):
        with transaction.atomic():
            claimed = (
                Task.objects
                .filter(
                    pk=self.pk,
                    type=TaskType.ONEOFF,
                    is_active=True,
                    is_accomplished=False,
                )
                .update(is_accomplished=True, accomplished_by=user)
            )
            if not claimed:
                return False

            Avatar.objects.filter(user=user).update(points=F("points") + 1)
        return True

    def unaccomplish(self):
        with transaction.atomic():
            task = (
                Task.objects
                .select_for_update()
                .filter(pk=self.pk, is_accomplished=True)
                .first()
            )
            if task is None:
                return False

            earner_id = task.accomplished_by_id
            Task.objects.filter(pk=self.pk).update(
                is_accomplished=False,
                accomplished_by=None,
            )
            if earner_id:
                Avatar.objects.filter(user_id=earner_id).update(
                    points=F("points") - 1
                )
        return True

    class Meta:
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "type"],
                condition=Q(type__in=SINGLETON_TYPES),
                name="one_singleton_per_unit",
            ),
            models.CheckConstraint(
                condition=Q(is_active=True) | ~Q(type__in=SINGLETON_TYPES),
                name="singletons_always_active",
            ),
            models.CheckConstraint(
                condition=Q(due_date__isnull=True)
                          | Q(type__in=[TaskType.ONEOFF, TaskType.LIST]),
                name="due_date_only_oneoff_or_list",
            ),
            models.CheckConstraint(
                condition=Q(is_accomplished=False) | Q(type=TaskType.ONEOFF),
                name="only_oneoff_accomplished",
            ),
            models.CheckConstraint(
                condition=Q(accomplished_by__isnull=True) | Q(is_accomplished=True),
                name="accomplished_by_needs_accomplished",
            ),
        ]
