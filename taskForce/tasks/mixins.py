from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import CheckConstraint, F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.managers import RecurringItemManager, CheckableItemManager


User = get_user_model()


def _add_points(user_id, delta):
    from taskForce.accounts.models import Avatar

    Avatar.objects.filter(user_id=user_id).update(points=F("points") + delta)


class CheckableItem(models.Model):
    is_checked = models.BooleanField(
        default=False,
        verbose_name=_("checked"),
    )

    checked_by = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("checked by"),
    )

    objects = CheckableItemManager()

    @property
    def is_done(self):
        return self.is_checked

    def tick(self, user):
        with transaction.atomic():
            claimed = (
                type(self).objects
                .filter(pk=self.pk, is_checked=False)
                .update(is_checked=True, checked_by=user)
            )
            if not claimed:
                return False
            _add_points(user.pk, 1)
        return True

    def untick(self):
        with transaction.atomic():
            item = (
                type(self).objects
                .select_for_update()
                .filter(pk=self.pk, is_checked=True)
                .first()
            )
            if item is None:
                return False
            earner_id = item.checked_by_id
            type(self).objects.filter(pk=self.pk).update(
                is_checked=False,
                checked_by=None,
            )
            if earner_id:
                _add_points(earner_id, -1)
        return True

    class Meta:
        abstract = True


class RecurringItem(models.Model):
    frequency_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("every (days)"),
    )
    last_done_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("last done at"),
    )
    previous_done_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("previously done at"),
    )

    objects = RecurringItemManager()

    @property
    def is_recurring(self):
        return self.frequency_days is not None

    @property
    def is_due_now(self):
        if self.frequency_days is None:
            return False
        if self.last_done_at is None:
            return True
        return self.last_done_at + timedelta(days=self.frequency_days) <= timezone.now()

    @property
    def is_done(self):
        if self.frequency_days is None:
            return super().is_done
        return not self.is_due_now

    def tick(self, user):
        if self.frequency_days is None:
            return super().tick(user)
        with transaction.atomic():
            item = type(self).objects.select_for_update().get(pk=self.pk)
            if not item.is_due_now:
                return False
            type(self).objects.filter(pk=self.pk).update(
                previous_done_at=item.last_done_at,
                last_done_at=timezone.now(),
                checked_by=user,
            )
            _add_points(user.pk, 1)
        return True

    def untick(self):
        if self.frequency_days is None:
            return super().untick()
        with transaction.atomic():
            item = type(self).objects.select_for_update().get(pk=self.pk)
            if item.is_due_now or item.checked_by_id is None:
                return False
            type(self).objects.filter(pk=self.pk).update(
                last_done_at=item.previous_done_at,
                previous_done_at=None,
                checked_by=None,
            )
            _add_points(item.checked_by_id, -1)
        return True

    def need_now(self):
        type(self).objects.filter(pk=self.pk).update(
            last_done_at=None,
            previous_done_at=None,
            checked_by=None,
        )

    class Meta:
        abstract = True


def checkable_constraints(model_name):
    return [
        CheckConstraint(
            condition=Q(checked_by__isnull=True) | Q(is_checked=True),
            name=f"{model_name}_checked_by_needs_checked",
        ),
    ]


def recurring_checkable_constraints(model_name):
    return [
        CheckConstraint(
            condition=Q(is_checked=False) | Q(frequency_days__isnull=True),
            name=f"{model_name}_recurring_never_checked",
        ),
        CheckConstraint(
            condition=Q(checked_by__isnull=True)
            | Q(is_checked=True)
            | Q(frequency_days__isnull=False),
            name=f"{model_name}_checked_by_needs_checked",
        ),
    ]


# --- Add to taskForce/tasks/mixins.py, after RecurringItem ------------------


def week_date(weekday, today):
    """The date of `weekday` (0 = Monday) in the week that contains `today`."""
    return today - timedelta(days=today.weekday()) + timedelta(days=weekday)


class WeeklyItem(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")
        SATURDAY = 5, _("Saturday")
        SUNDAY = 6, _("Sunday")

    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        null=True,
        blank=True,
        verbose_name=_("weekday"),
    )
    last_done_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("last done at"),
    )
    previous_done_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("previously done at"),
    )

    @property
    def is_planned(self):
        return self.weekday is not None

    def scheduled_date(self):
        if self.weekday is None:
            return None
        return week_date(self.weekday, timezone.localdate())

    @property
    def is_done(self):
        day = self.scheduled_date()
        return (
            day is not None
            and self.last_done_at is not None
            and timezone.localdate(self.last_done_at) >= day
        )

    @property
    def is_open(self):
        day = self.scheduled_date()
        return day is not None and day <= timezone.localdate() and not self.is_done

    @property
    def is_missed(self):
        day = self.scheduled_date()
        return day is not None and day < timezone.localdate() and not self.is_done

    @property
    def is_upcoming(self):
        day = self.scheduled_date()
        return day is not None and day > timezone.localdate()

    def tick(self, user):
        with transaction.atomic():
            item = type(self).objects.select_for_update().get(pk=self.pk)
            if not item.is_open:
                return False
            type(self).objects.filter(pk=self.pk).update(
                previous_done_at=item.last_done_at,
                last_done_at=timezone.now(),
                checked_by=user,
            )
            _add_points(user.pk, 1)
        return True

    def untick(self):
        with transaction.atomic():
            item = type(self).objects.select_for_update().get(pk=self.pk)
            if not item.is_done or item.checked_by_id is None:
                return False
            type(self).objects.filter(pk=self.pk).update(
                last_done_at=item.previous_done_at,
                previous_done_at=None,
                checked_by=None,
            )
            _add_points(item.checked_by_id, -1)
        return True

    class Meta:
        abstract = True


def weekly_checkable_constraints(model_name):
    return [
        CheckConstraint(
            condition=Q(is_checked=False),
            name=f"{model_name}_weekly_never_checked",
        ),
        CheckConstraint(
            condition=Q(weekday__isnull=True) | Q(weekday__lte=6),
            name=f"{model_name}_weekday_range",
        ),
    ]