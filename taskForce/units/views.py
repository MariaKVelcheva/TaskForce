from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView, FormView
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from taskForce.units.forms import CreateUnitForm, JoinUnitForm, RenameUnitForm
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
        unit_tasks = self.object.tasks.all()

        context["is_commander"] = self.object.memberships.filter(
            user=self.request.user,
            role="commander").exists()

        if context["is_commander"]:
            context["invite_url"] = self.object.get_invite_url(self.request)

        context["unit_tasks"] = unit_tasks
        context["active_tasks"] = unit_tasks.filter(is_done=False)
        context["finished_tasks"] = unit_tasks.filter(is_done=False)

        return context


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