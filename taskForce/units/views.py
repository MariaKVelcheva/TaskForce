from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView, FormView
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import Task
from taskForce.units.forms import CreateUnitForm, JoinUnitForm, RenameUnitForm, ChangeCommanderForm
from taskForce.units.models import Unit, Membership

TaskUser = get_user_model()


class CreateUnitView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = CreateUnitForm
    template_name = "units/create-unit.html"

    def get_success_url(self):
        return reverse_lazy("details-unit", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        Membership.objects.create(
            user=self.request.user,
            role="commander",
            unit=self.object,
        )

        return response


class RenameUnitView(LoginRequiredMixin, UpdateView):
    model = Unit
    form_class = RenameUnitForm
    template_name = "units/rename-unit.html"

    def get_queryset(self):
        return Unit.objects.filter(
            memberships__user=self.request.user,
            memberships__role="commander",
        )

    def get_success_url(self):
        return reverse_lazy("details-unit", kwargs={"pk": self.object.pk})


class DeleteUnitView(LoginRequiredMixin, DeleteView):
    model = Unit
    template_name = "units/delete-unit.html"
    success_url = reverse_lazy("home")

    def get_queryset(self):
        return Unit.objects.filter(
            memberships__user=self.request.user,
            memberships__role="commander",
        )


class DetailUnitView(LoginRequiredMixin, DetailView):
    model = Unit
    template_name = "units/details-unit.html"
    context_object_name = "unit"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.object
        tasks = unit.tasks.all()
        memberships = unit.memberships.select_related("user").order_by("role", "user__username")

        is_commander = any(
            m.role == "commander" and m.user == self.request.user for m in memberships
        )

        context["is_commander"] = is_commander
        context["can_leave"] = not is_commander
        context["memberships"] = memberships
        context["active_tasks"] = tasks.filter(is_done=False)
        context["finished_tasks"] = tasks.filter(is_done=True)

        return context

    def get_queryset(self):
        return Unit.objects.filter(memberships__user=self.request.user)


class CatalogueUnitView(LoginRequiredMixin, ListView):
    model = Unit
    template_name = "units/catalogue-unit.html"
    context_object_name = "units"

    def get_queryset(self):
        return Unit.objects.filter(memberships__user=self.request.user)


class JoinUnitView(LoginRequiredMixin, FormView):
    template_name = "units/join-unit.html"
    form_class = JoinUnitForm

    def get_initial(self):
        initial = super().get_initial()
        code = self.request.GET.get("code")

        if code:
            initial["invite_code"] = code

        return initial

    def form_valid(self, form):
        unit = form.unit

        membership, created = Membership.objects.get_or_create(
            user=self.request.user,
            unit=unit,
            defaults={"role": "operative"},
        )

        if created:
            messages.success(self.request, _("You have joined %(name)s.") % {"name": unit.name})
        else:
            messages.info(self.request, _("You are already a member of this unit."))

        return redirect("details-unit", pk=unit.pk)


@login_required
@require_POST
def remove_member(request, pk, membership_pk):
    unit = get_object_or_404(Unit.objects.filter(
        memberships__user=request.user,
        memberships__role="commander",
    ), pk=pk)

    membership = get_object_or_404(
        unit.memberships, pk=membership_pk
    )

    if membership.user == request.user:
        messages.info(request, "Use Leave to stand down from a unit.")
        return redirect("details-unit", pk=unit.pk)

    with transaction.atomic():
        Task.objects.filter(unit=unit, assigned_to=membership.user).update(assigned_to=None)
        membership.delete()

    return redirect("details-unit", pk=unit.pk)


@login_required
@require_POST
def transfer_command(request, pk, membership_pk):
    commander = request.user

    unit = get_object_or_404(
        Unit.objects.filter(
                            memberships__user=commander,
                            memberships__role="commander"),
        pk=pk,
    )

    membership = get_object_or_404(
        unit.memberships, pk=membership_pk,

    )

    with transaction.atomic():
        unit.memberships.filter(role="commander").update(role="operative")
        membership.role = "commander"
        membership.save(update_fields=["role"])

    return redirect("details-unit", pk=unit.pk)


@login_required
@require_POST
def leave_unit(request, unit_pk):
    unit = get_object_or_404(
        Unit.objects.filter(memberships__user=request.user), pk=unit_pk
    )

    if unit.memberships.filter(user=request.user, role="commander").exists():
        raise PermissionDenied

    with transaction.atomic():
        Task.objects.filter(
            unit=unit,
            assigned_to=request.user,
            is_done=False,
        ).update(assigned_to=None)
        unit.memberships.filter(user=request.user).delete()

    return redirect("all-units")