from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView

from taskForce.tasks.forms import CreateTaskForm, UpdateTaskForm, QuickCreateTaskForm
from taskForce.tasks.models import Task


class CreateTaskView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = CreateTaskForm
    template_name = "tasks/add-task.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("details-task", kwargs={"pk": self.object.pk})


class DetailTaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/details-task.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.visible_to(self.request.user)


class UpdateTaskView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = UpdateTaskForm
    template_name = "tasks/update-task.html"

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("details-task", kwargs={"pk": self.object.pk})


class DeleteTaskView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/delete-task.html"

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy("home")


class CatalogueTaskView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/catalogue-tasks.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        queryset = Task.objects.visible_to(self.request.user)

        task_type = self.request.GET.get("type")
        if task_type == "none":
            queryset = queryset.filter(type__isnull=True)
        elif task_type:
            queryset = queryset.filter(type=task_type)

        if self.request.GET.get("show") != "all":
            queryset = queryset.filter(is_done=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_filter_context())
        return context

    def get_filter_context(self):
        return {
            "type_choices": Task.TYPE_CHOICES,
            "active_type": self.request.GET.get("type", ""),
            "show_all": self.request.GET.get("show") == "all",
        }


@login_required
@require_POST
def complete_task(request, pk):
    task = get_object_or_404(Task.objects.visible_to(request.user), pk=pk)

    if not task.complete(request.user):
        messages.info(request, "Mission already accomplished by another operative.")

    return redirect("details-task", pk=task.pk)


@login_required
@require_POST
def uncomplete_task(request, pk):
    task = get_object_or_404(Task.objects.visible_to(request.user), pk=pk)

    if request.user not in (task.assigned_to, task.user):
        raise PermissionDenied

    if not task.uncomplete():
        messages.info(request, "That mission is not marked as accomplished.")

    return redirect("details-task", pk=task.pk)

