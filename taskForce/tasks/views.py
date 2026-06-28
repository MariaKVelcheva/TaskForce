from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView

from taskForce.tasks.forms import CreateTaskForm, UpdateTaskForm
from taskForce.tasks.models import Task


class CreateTaskView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = CreateTaskForm
    template_name = "tasks/add-task.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("details-task", kwargs={"pk": self.object.pk})


class DetailTaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/details-task.html"

    def get_queryset(self, *args, **kwargs):
        return Task.objects.filter(user=self.request.user)


class UpdateTaskView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = UpdateTaskForm
    template_name = "tasks/update-task.html"

    def get_queryset(self, *args, **kwargs):
        return Task.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy("details-task", kwargs={"pk": self.object.pk})


class DeleteTaskView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/delete-task.html"

    def get_queryset(self, *args, **kwargs):
        return Task.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy("home")


class CatalogueTaskView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/catalogue-tasks.html"
    context_object_name = "tasks"

    def get_queryset(self, *args, **kwargs):
        return Task.objects.filter(user=self.request.user)


@login_required
@require_POST
def complete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.complete(request.user)
    return redirect("details-task", pk=task.id)

