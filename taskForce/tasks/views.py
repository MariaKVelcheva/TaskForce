from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from taskForce.redirects import NextMixin, get_next, with_next
from taskForce.tasks.forms import CreateTaskForm, UpdateTaskForm
from taskForce.tasks.items import ITEM_FORMS, ITEM_MODELS, ITEM_PARTIALS
from taskForce.tasks.mixins import CheckableItem, RecurringItem
from taskForce.tasks.models import SINGLETON_TYPES, Task, TaskType
from taskForce.tasks.urgency import with_urgency
from taskForce.units.models import Membership
from taskForce.units.services import active_unit_for


def get_item_context(task):
    item_model = ITEM_MODELS.get(task.type)
    if item_model is None:
        return {"items": None}

    items = list(item_model.objects.filter(task=task))
    checkable = issubclass(item_model, CheckableItem)

    return {
        "items": items,
        "item_form": ITEM_FORMS[task.type](),
        "items_done": sum(1 for item in items if item.is_done) if checkable else None,
        "items_total": len(items),
        "item_partial": ITEM_PARTIALS[task.type],
        "task": task,
    }


def get_task_and_item_model(user, task_pk):
    task = get_object_or_404(Task.objects.visible_to(user), pk=task_pk)

    item_model = ITEM_MODELS.get(task.type)
    if item_model is None:
        raise Http404

    return task, item_model


def _item_response(request, task):
    if request.headers.get("x-requested-with") == "fetch":
        context = get_item_context(task)
        context["next_url"] = get_next(request)
        return render(request, context["item_partial"], context)
    return redirect(with_next(reverse("details-task", args=[task.pk]), get_next(request)))


def _back_to_task(request, task):
    return redirect(get_next(request) or reverse("details-task", args=[task.pk]))


def _manageable(user):
    return Task.objects.visible_to(user).exclude(type__in=SINGLETON_TYPES)


class CreateTaskView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = CreateTaskForm
    template_name = "tasks/add-task.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["unit"] = active_unit_for(self.request.user)
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return with_next(reverse("details-task", args=[self.object.pk]), get_next(self.request))


class DetailTaskView(NextMixin, LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/details-task.html"
    context_object_name = "task"

    def get_queryset(self):
        return with_urgency(Task.objects.visible_to(self.request.user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_item_context(self.object))
        context.update(self.get_next_context())
        is_singleton = self.object.type in SINGLETON_TYPES
        context["is_singleton"] = is_singleton
        context["show_switch_hint"] = (
                is_singleton
                and Membership.objects.filter(user=self.request.user).count() > 1
        )
        return context


class UpdateTaskView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = UpdateTaskForm
    template_name = "tasks/update-task.html"

    def get_queryset(self):
        return Task.objects.visible_to(self.request.user).filter(is_active=True)

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
        return Task.objects.filter(user=self.request.user).exclude(type__in=SINGLETON_TYPES)

    def get_success_url(self):
        return get_next(self.request) or reverse("all-tasks")


@login_required
@require_POST
def accomplish_task(request, pk):
    task = get_object_or_404(
        Task.objects.visible_to(request.user), pk=pk, type=TaskType.ONEOFF,
    )
    if task.accomplish(request.user):
        messages.success(request, _("Mission accomplished. +1 pt"))
    return _back_to_task(request, task)


@login_required
@require_POST
def unaccomplish_task(request, pk):
    task = get_object_or_404(
        Task.objects.visible_to(request.user), pk=pk, type=TaskType.ONEOFF,
    )
    task.unaccomplish()
    return _back_to_task(request, task)


@login_required
@require_POST
def deactivate_task(request, pk):
    task = get_object_or_404(_manageable(request.user), pk=pk)
    Task.objects.filter(pk=task.pk).update(is_active=False)
    return _back_to_task(request, task)


@login_required
@require_POST
def reactivate_task(request, pk):
    task = get_object_or_404(_manageable(request.user), pk=pk, is_accomplished=False)
    Task.objects.filter(pk=task.pk).update(is_active=True)
    return _back_to_task(request, task)


class CatalogueTaskView(LoginRequiredMixin, ListView):
    SORT_OPTIONS = [
        ("newest", _("Newest")),
        ("due", _("Due date")),
        ("priority", _("Priority")),
        ("name", _("Name")),
    ]

    ORDERINGS = {
        "priority": ["priority"],
        "due": [F("due_date").asc(nulls_last=True), "-created_at"],
        "name": ["name"],
        "newest": ["-created_at"],
    }

    model = Task
    template_name = "tasks/catalogue-tasks.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        queryset = with_urgency(Task.objects.visible_to(self.request.user))

        task_type = self.request.GET.get("type")
        if task_type == "none":
            queryset = queryset.filter(type=TaskType.ONEOFF)
        elif task_type:
            queryset = queryset.filter(type=task_type)

        if self.request.GET.get("show") != "all":
            queryset = queryset.filter(is_active=True)

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(unit__name__icontains=search)
                | Q(assigned_to__username__icontains=search)
            )

        ordering = self.ORDERINGS.get(
            self.request.GET.get("order"), self.ORDERINGS["newest"]
        )
        return queryset.order_by(*ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_filter_context())
        return context

    def get_filter_context(self):
        return {
            "type_choices": [
                ("none" if value == TaskType.ONEOFF else value, label)
                for value, label in TaskType.choices
            ],
            "sort_options": self.SORT_OPTIONS,
            "active_type": self.request.GET.get("type", ""),
            "show_all": self.request.GET.get("show") == "all",
            "active_order": self.request.GET.get("order", "newest"),
        }


@login_required
@require_POST
def add_item(request, task_pk):
    task, _item_model = get_task_and_item_model(request.user, task_pk)

    form = ITEM_FORMS[task.type](request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.task = task
        item.save()
    else:
        for errors in form.errors.values():
            messages.error(request, errors[0])

    return _item_response(request, task)


@login_required
@require_POST
def toggle_item(request, task_pk, item_pk):
    task, item_model = get_task_and_item_model(request.user, task_pk)
    if not issubclass(item_model, CheckableItem):
        raise Http404

    item = get_object_or_404(item_model, pk=item_pk, task=task)
    if item.is_done:
        item.untick()
    else:
        item.tick(request.user)

    return _item_response(request, task)


@login_required
@require_POST
def need_item_now(request, task_pk, item_pk):
    task, item_model = get_task_and_item_model(request.user, task_pk)
    if not issubclass(item_model, RecurringItem):
        raise Http404

    item = get_object_or_404(item_model, pk=item_pk, task=task)
    item.need_now()
    return _item_response(request, task)


@login_required
@require_POST
def delete_item(request, task_pk, item_pk):
    task, item_model = get_task_and_item_model(request.user, task_pk)

    item = get_object_or_404(item_model, pk=item_pk, task=task)
    item.delete()

    return _item_response(request, task)