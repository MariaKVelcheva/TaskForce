from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView

from taskForce.tasks.models import Task
from taskForce.units.forms import CreateUnitForm, UpdateUnitForm
from taskForce.units.models import Unit, Membership


class CreateUnitView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = CreateUnitForm
    template_name = "units/create-unit.html"

    def get_success_url(self):
        return reverse_lazy("unit-details", kwargs={"pk": self.object.pk})

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

    def get_success_url(self):
        return reverse_lazy("unit-details", kwargs={"pk": self.object.pk})


class DeleteUnitView(LoginRequiredMixin, DeleteView):
    model = Unit
    template_name = "units/delete-unit.html"
    success_url = reverse_lazy("home")


class DetailUnitView(LoginRequiredMixin, DetailView):
    model = Unit
    template_name = "units/details-unit.html"
    context_object_name = "unit"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["active_tasks"] = self.get_queryset().filter(is_done=False)
        context["finished_tasks"] = self.get_queryset().filter(is_done=True)
       # context["is_commander"] = self.object.memberships.filter(role="commander").exists()

        return context


class CatalogueUnitView(LoginRequiredMixin, ListView):
    model = Unit
    template_name = "units/catalogue-unit.html"
    context_object_name = "units"

    def get_queryset(self):
        return Unit.objects.filter(membership__user=self.request.user)




