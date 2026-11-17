import operator
from datetime import timedelta, datetime, time
from functools import reduce

from django.db import models
from django.db.models import DateTimeField, Exists, ExpressionWrapper, F, OuterRef, Q
from django.db.models.functions import Now
from django.utils import timezone


def week_date(weekday, today):
    return today - timedelta(days=today.weekday()) + timedelta(days=weekday)


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


class CheckableItemManager(TaskItemManager):
    def done(self, now=None):
        return self.filter(is_checked=True)


class PantryItemManager(TaskItemManager):
    def low(self):
        return self.filter(threshold__isnull=False, quantity__lte=F("threshold"))


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

    def done(self, now=None):
        now = Now() if now is None else now
        return self.annotate(due_at=self.DUE_AT).filter(
            Q(frequency_days__isnull=True, is_checked=True)
            | Q(frequency_days__isnull=False, last_done_at__isnull=False, due_at__gt=now)
        )

    @staticmethod
    def pending_q(now):
        return (
            Q(frequency_days__isnull=True, is_checked=False)
            | Q(frequency_days__isnull=False, last_done_at__isnull=True)
            | Q(frequency_days__isnull=False, due_at__lte=now)
        )

    def pending(self, now=None):
        now = Now() if now is None else now
        return self.annotate(due_at=self.DUE_AT).filter(self.pending_q(now))


class WeeklyItemManager(CheckableItemManager):
    @staticmethod
    def done_q(now=None):
        today = timezone.localdate(now)
        return reduce(operator.or_, (
            Q(weekday=day, last_done_at__gte=timezone.make_aware(
                datetime.combine(week_date(day, today), time.min)
            ))
            for day in range(7)
        ))

    def done(self, now=None):
        return self.filter(self.done_q(now))