from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Spending(models.Model):
    unit = models.ForeignKey(
        to="units.Unit",
        on_delete=models.CASCADE,
        related_name="spendings",
        verbose_name=_("unit"),
    )

    task = models.ForeignKey(
        to="tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="spendings",
        verbose_name=_("mission"),
    )

    amount = models.DecimalField(
        verbose_name=_("amount"),
        max_digits=10,
        decimal_places=2,
    )

    spent_on = models.DateField(
        verbose_name=_("spent on"),
        default=timezone.localdate,
    )

    added_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="spendings",
        verbose_name=_("added by"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.task_id and self.task.unit_id != self.unit_id:
            raise ValidationError({"task": _("This mission belongs to another unit.")})

    def __str__(self):
        return f"{self.amount} € on {self.spent_on} ({self.unit})"

    class Meta:
        verbose_name = _("spending")
        verbose_name_plural = _("spendings")
        ordering = ("-spent_on", "-created_at")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="spending_amount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["unit", "spent_on"], name="spending_unit_month_idx"),
        ]