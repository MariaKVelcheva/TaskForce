from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from taskForce.budget.models import Spending
from taskForce.units.services import commanded_by


@dataclass(frozen=True)
class Funds:
    spent: Decimal
    budget: Decimal | None
    is_unit_fallback: bool = False

    @property
    def has_budget(self):
        return self.budget is not None

    @property
    def is_over(self):
        return self.has_budget and self.spent > self.budget

    @property
    def remaining(self):
        if not self.has_budget:
            return None
        return max(self.budget - self.spent, Decimal("0"))

    @property
    def overrun(self):
        if not self.has_budget:
            return None
        return max(self.spent - self.budget, Decimal("0"))


def month_range(day):
    start = day.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def _spent_in_month(spendings, day):
    start, end = month_range(day)
    total = spendings.filter(spent_on__gte=start, spent_on__lt=end).aggregate(total=Sum("amount"))["total"]
    return total or Decimal("0")


def unit_funds(unit, day=None):
    day = day or timezone.localdate()
    return Funds(spent=_spent_in_month(unit.spendings.all(), day), budget=unit.monthly_budget)


def task_funds(task, day=None):
    day = day or timezone.localdate()
    if task.monthly_budget is None:
        unit = unit_funds(task.unit, day)
        return Funds(spent=unit.spent, budget=unit.budget, is_unit_fallback=True)
    return Funds(spent=_spent_in_month(task.spendings.all(), day), budget=task.monthly_budget)


def log_spending(*, amount, added_by, unit=None, task=None, spent_on=None):
    if task is not None:
        unit = task.unit
    spending = Spending(
        unit=unit,
        task=task,
        amount=amount,
        added_by=added_by,
        spent_on=spent_on or timezone.localdate(),
    )
    spending.full_clean()
    spending.save()
    return spending


def can_delete_spending(spending, user):
    if spending.added_by_id == user.id:
        return True
    return commanded_by(user).filter(pk=spending.unit_id).exists()


def funds_panel(*, user, unit, task=None, day=None):
    day = day or timezone.localdate()
    start, end = month_range(day)

    scope = task.spendings.all() if task else unit.spendings.all()
    spendings = list(
        scope.filter(spent_on__gte=start, spent_on__lt=end).select_related("added_by", "task")
    )
    is_commander = commanded_by(user).filter(pk=unit.pk).exists()
    for spending in spendings:
        spending.can_delete = is_commander or spending.added_by_id == user.id

    if task:
        log_url = reverse("mission-log-spending", args=[task.pk])
        budget_url = reverse("mission-set-budget", args=[task.pk])
    else:
        log_url = reverse("unit-log-spending", args=[unit.pk])
        budget_url = reverse("unit-set-budget", args=[unit.pk])

    return {
        "unit": unit,
        "task": task,
        "today": day,
        "funds": task_funds(task, day) if task else unit_funds(unit, day),
        "budget_value": (task or unit).monthly_budget,
        "spendings": spendings,
        "log_url": log_url,
        "budget_url": budget_url,
        "anchor": f"funds-{task.pk}" if task else "funds",
    }

