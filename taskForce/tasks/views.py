from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, F
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, ListView

from taskForce.redirects import NextMixin, with_next, get_next
from taskForce.tasks.forms import CreateTaskForm, UpdateTaskForm, QuickCreateTaskForm
from taskForce.tasks.items import ITEM_MODELS, ITEM_FORMS, ITEM_PARTIALS
from taskForce.tasks.models import Task, ChoreItem


def get_item_context(task):
    item_model = ITEM_MODELS.get(task.type)
    item_partial = ITEM_PARTIALS.get(task.type)

    if item_model is None:
        return {"items": None}

    items = list(item_model.objects.with_due_state().filter(task=task))

    return {
        "items": items,
        "item_form": ITEM_FORMS[task.type](),
        "items_done": sum(1 for item in items if item.is_active), #fix
        "items_total": len(items),
        "item_partial": item_partial,
        "task": task,
    }


def get_task_and_item_model(user, task_pk):
    task = get_object_or_404(Task.objects.visible_to(user), pk=task_pk)

    item_model = ITEM_MODELS.get(task.type)
    if item_model is None:
        raise Http404

    return task, item_model


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
        return with_next(reverse("details-task", args=[self.object.pk]), get_next(self.request))


class DetailTaskView(NextMixin, LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/details-task.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_item_context(self.object))
        context.update(self.get_next_context())
        return context


class UpdateTaskView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = UpdateTaskForm
    template_name = "tasks/update-task.html"

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user, is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return with_next(reverse("details-task", args=[self.object.pk]), get_next(self.request))


class DeleteTaskView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/delete-task.html"

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_success_url(self):
        return get_next(self.request) or reverse("all-tasks")


class CatalogueTaskView(LoginRequiredMixin, ListView):
    SORT_OPTIONS = [
        ("newest", "Newest"),
        ("due", "Due date"),
        ("priority", "Priority"),
        ("name", "Name"),
    ]

    ORDERINGS = {
        "priority": ["priority", ],
        "due": [F("due_date").asc(nulls_last=True), "-created_at"],
        "name": ["name"],
        "newest": ["-created_at"],
    }

    model = Task
    template_name = "tasks/catalogue-tasks.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        due_chore_tasks = ChoreItem.objects.due().values_list("task_id", flat=True)

        queryset = Task.objects.visible_to(self.request.user).annotate(
            needs_attention=Q(pk__in=due_chore_tasks)
        )

        task_type = self.request.GET.get("type")
        if task_type == "none":
            queryset = queryset.filter(type__isnull=True)
        elif task_type:
            queryset = queryset.filter(type=task_type)

        if self.request.GET.get("show") != "all":
            queryset = queryset.filter(is_done=False)

        ordering = self.ORDERINGS.get(
            self.request.GET.get("order"), self.ORDERINGS["newest"]
        )

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(unit__name__icontains=search)
                | Q(assigned_to__username__icontains=search)
            )

        return queryset.order_by(*ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_filter_context())
        return context

    def get_filter_context(self):
        return {
            "type_choices": Task.TYPE_CHOICES,
            "active_type": self.request.GET.get("type", ""),
            "show_all": self.request.GET.get("show") == "all",
            "active_order": self.request.GET.get("order", "newest"),
        }

@login_required
@require_POST
def toggle_item(request, task_pk, item_pk):
    task, item_model = get_task_and_item_model(request.user, task_pk)

    item = get_object_or_404(item_model.objects.with_due_state(), pk=item_pk, task=task)
    item.toggle()

    if request.headers.get("x-requested-with") == "fetch":
        context = get_item_context(task)
        context["next_url"] = get_next(request)
        return render(request, context["item_partial"], context)

    return with_next(reverse("details-task", args=[task.pk]), get_next(request))


@login_required
@require_POST
def delete_item(request, task_pk, item_pk):
    task, item_model = get_task_and_item_model(request.user, task_pk)

    if item_model is None:
        raise Http404

    item = get_object_or_404(item_model, pk=item_pk, task=task)
    item.delete()

    if request.headers.get("x-requested-with") == "fetch":
        context = get_item_context(task)
        context["next_url"] = get_next(request)
        return render(request, context["item_partial"], context)

    return with_next(reverse("details-task", args=[task.pk]), get_next(request))


@login_required
@require_POST
def add_item(request, task_pk):
    task, _ = get_task_and_item_model(request.user, task_pk)

    form_class = ITEM_FORMS.get(task.type)
    form = form_class(request.POST)

    if form.is_valid():
        item = form.save(commit=False)
        item.task = task
        item.save()
    else:
        for error in form.errors.values():
            messages.error(request, error[0])

    if request.headers.get("x-requested-with") == "fetch":
        context = get_item_context(task)
        context["next_url"] = get_next(request)
        return render(request, context["item_partial"], context)

    return redirect("details-task", pk=task.pk)

