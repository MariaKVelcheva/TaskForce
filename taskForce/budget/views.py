from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from taskForce.budget.forms import BudgetForm, SpendingForm
from taskForce.budget.models import Spending
from taskForce.budget.services import can_delete_spending, log_spending
from taskForce.redirects import get_next
from taskForce.tasks.models import Task
from taskForce.units.models import Unit


def _target(user, unit_pk=None, task_pk=None):
    if task_pk is not None:
        task = get_object_or_404(
            Task.objects.filter(unit__memberships__user=user).select_related("unit"),
            pk=task_pk,
        )
        return task.unit, task
    unit = get_object_or_404(Unit.objects.filter(memberships__user=user), pk=unit_pk)
    return unit, None


def _back(request, unit, task):
    if task:
        fallback = reverse("details-task", args=[task.pk])
    else:
        fallback = reverse("details-unit", args=[unit.pk])
    return redirect(get_next(request) or fallback)


@login_required
@require_POST
def log_spending_view(request, unit_pk=None, task_pk=None):
    unit, task = _target(request.user, unit_pk, task_pk)
    form = SpendingForm(request.POST)
    if form.is_valid():
        log_spending(
            amount=form.cleaned_data["amount"],
            added_by=request.user,
            unit=unit,
            task=task,
            spent_on=form.cleaned_data["spent_on"],
        )
        messages.success(request, _("Spending logged."))
    else:
        messages.error(request, _("Enter an amount above zero."))
    return _back(request, unit, task)


@login_required
@require_POST
def set_budget_view(request, unit_pk=None, task_pk=None):
    unit, task = _target(request.user, unit_pk, task_pk)
    form = BudgetForm(request.POST)
    if form.is_valid():
        target = task or unit
        target.monthly_budget = form.cleaned_data["monthly_budget"]
        target.save(update_fields=["monthly_budget"])
        if target.monthly_budget is None:
            messages.success(request, _("Budget removed."))
        else:
            messages.success(request, _("Budget updated."))
    else:
        messages.error(request, _("A budget must be above zero, or left empty."))
    return _back(request, unit, task)


@login_required
@require_POST
def delete_spending_view(request, pk):
    spending = get_object_or_404(
        Spending.objects.filter(unit__memberships__user=request.user).select_related("unit", "task"),
        pk=pk,
    )
    if not can_delete_spending(spending, request.user):
        raise PermissionDenied
    spending.delete()
    messages.success(request, _("Entry deleted."))
    return _back(request, spending.unit, spending.task)

