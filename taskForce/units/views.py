from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from taskForce.units.forms import CreateUnitForm, UpdateUnitForm
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


class UpdateUnitView(LoginRequiredMixin, UpdateView):
    model = Unit
    form_class = UpdateUnitForm
    template_name = "units/update-unit.html"

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


@login_required
def join_unit(request, invite_code):
    unit = Unit.objects.filter(
        invite_code=invite_code,
    ).first()

    if not unit:
        raise Http404(_("Unit does not exist"))

    user = request.user

    if unit.memberships.filter(user=user).exists():
        messages.info(request, _("You are already a member of this unit."))
        return redirect("details-unit", pk=unit.pk)

    if request.method == "POST":
        Membership.objects.create(
            user=user,
            role="operative",
            unit=unit,
        )
        messages.success(request,
                         f"You have successfully joined {unit.name}")
        return redirect("details-unit", pk=unit.pk)

    context = {
        "user": user,
        "invite_code": invite_code,
        "unit": unit
    }

    return render(request, "units/join-unit.html", context)

