from datetime import timedelta

from django.db import models
from django.db.models import DateTimeField, Exists, ExpressionWrapper, F, OuterRef, Q
from django.db.models.functions import Now


class TaskManager(models.Manager):
    def active(self):
        return self.filter(is_active=True).order_by("-created_at")

    def visible_to(self, user):
        from taskForce.units.models import Membership

        my_membership = Membership.objects.filter(unit=OuterRef("unit"), user=user)
        return (
            self.filter(Exists(my_membership))
            .select_related("unit", "assigned_to", "user")
        )


class TaskItemManager(models.Manager):
    def with_due_state(self):
        return self.get_queryset()


class RecurringItemManager(TaskItemManager):
    DUE_AT = ExpressionWrapper(
        F("last_done_at") + timedelta(days=1) * F("frequency_days"),
        output_field=DateTimeField(),
    )

    @staticmethod
    def is_due_q(now):
        return Q(frequency_days__isnull=False) & (
            Q(last_done_at__isnull=True) | Q(due_at__lte=now)
        )

    def with_due_state(self, now=None):
        now = Now() if now is None else now
        return self.annotate(due_at=self.DUE_AT).annotate(is_due=self.is_due_q(now))

    def due(self, now=None):
        now = Now() if now is None else now
        return self.annotate(due_at=self.DUE_AT).filter(self.is_due_q(now))