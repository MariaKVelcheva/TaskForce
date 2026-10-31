from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.db.models import CheckConstraint, F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.manager import RecurringItemManager


def _add_points(user_id, delta):
    from taskForce.accounts.models import Avatar

    Avatar.objects.filter(user_id=user_id).update(points=F("points") + delta)


class CheckableItem(models.Model):
    is_checked = models.BooleanField(
        default=False,
        verbose_name=_("checked"),
    )
    checked_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("checked by"),
    )

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