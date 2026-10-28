from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q, OuterRef, Count, F, Subquery
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, ListView
from taskForce.common.deploy_map import TILE, building_positions, map_rows, tiles
from taskForce.tasks.locations import location_summary

from taskForce.comms.models import Message, ConversationRead
from taskForce.tasks.forms import QuickCreateTaskForm
from taskForce.tasks.items import ITEM_MODELS, item_progress
from taskForce.tasks.locations import LOCATIONS, missions_at
from taskForce.tasks.models import Task, TaskItem, ChoreItem
from taskForce.tasks.urgency import group_by_urgency, has_due_chores
from taskForce.units.models import Unit

TaskUser = get_user_model()


class IndexView(TemplateView):
    template_name = "common/index.html"


class DebriefHomeView(LoginRequiredMixin, TemplateView):
    template_name = "common/debrief-home.html"

    RECENT_MESSAGES = 5
    VISIBLE_UNITS = 4
    VISIBLE_TASKS = 5
    VISIBLE_OVER_DUE = 5

    def post(self, request, *args, **kwargs):
        form = QuickCreateTaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            if task.type in ITEM_MODELS:
                return redirect("details-task", pk=task.pk)
        else:
            for error in form.errors.get("name", []):
                messages.error(request, error)

        return redirect(request.get_full_path())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(self.get_task_context())
        context.update(self.get_unit_context())
        context.update(self.get_message_context())
        context.update(self.get_overdue_context())
        context.update(self.get_soon_due_context())

        avatar = getattr(self.request.user, "avatar", None)
        context["points"] = avatar.points if avatar else 0

        return context

    def get_task_context(self):
        tasks = Task.objects.visible_to(self.request.user)
        counts = tasks.aggregate(
            open=Count("pk", filter=Q(is_done=False), distinct=True),
            done=Count("pk", filter=Q(is_done=True), distinct=True),
        )
        return {
            "open_tasks": (
                tasks.filter(is_done=False)
                .order_by(F("due_date").asc(nulls_last=True), "-created_at")
                [:self.VISIBLE_TASKS]
            ),
            "quick_types": [
                (value, label) for value, label in Task.TYPE_CHOICES
                if value in ITEM_MODELS
            ],
            "open_tasks_count": counts["open"],
            "done_tasks_count": counts["done"],
        }

    def get_unit_context(self):
        return {
            "units": Unit.objects.filter(
                memberships__user=self.request.user
            ).annotate(
                user_count=Count("users", distinct=True)
            ).order_by("name")[:self.VISIBLE_UNITS]
        }

    def get_message_context(self):
        user = self.request.user
        last_read = ConversationRead.objects.filter(
            conversation=OuterRef("conversation"),
            user=user,
        ).values("last_read_at")[:1]

        return {
            "recent_messages": (
                Message.objects.filter(conversation__unit__memberships__user=user)
                .select_related("sender", "conversation", "conversation__unit", "conversation__task")
                .annotate(last_read_at=Subquery(last_read))
                .annotate(
                    is_read=Q(last_read_at__isnull=True) | Q(created_at__gt=F("last_read_at"))
                )
                .annotate(
                    is_unread=(Q(last_read_at__isnull=True) | Q(created_at__gt=F("last_read_at")))
                              & ~Q(sender=user)
                )
                .order_by("-created_at")[:self.RECENT_MESSAGES]
            )
        }

    def get_overdue_context(self):
        due_chore_tasks = ChoreItem.objects.due().values_list("task_id", flat=True)
        query = (Q(is_done=False) & Q(due_date__lt=timezone.now())) | Q(id__in=due_chore_tasks)

        return {
            "overdue_tasks": (
                Task.objects.visible_to(self.request.user)
                .filter(query)
                .annotate(has_due_duties=Q(pk__in=due_chore_tasks))
                .order_by(F("due_date").asc(nulls_last=True))[:self.VISIBLE_OVER_DUE]
            )
        }

    def get_soon_due_context(self):
        horizon = timezone.now() + timedelta(days=2)
        due_tasks = (Task.objects.visible_to(self.request.user)
                     .filter(is_done=False, due_date__gte=timezone.now(), due_date__lte=horizon)
                     .order_by("due_date")[:self.VISIBLE_OVER_DUE]
                     )
        return {"due_tasks": due_tasks}


class DeployIndexView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/../../templates/common/deploy-index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_locations_context())
        return context

    def get_locations_context(self):
        summary = location_summary(self.request.user)
        positions = building_positions()
        buildings = []
        for key, loc in LOCATIONS.items():
            col, row = positions[key]
            buildings.append({
                "key": key,
                "label": loc["label"],
                "x": col * TILE,
                "y": row * TILE,
                **summary[key],
            })
        rows = map_rows()
        return {
            "tiles": list(tiles()),
            "buildings": buildings,
            "map_width": len(rows[0]) * TILE,
            "map_height": len(rows) * TILE,
        }


class DeployLocationView(LoginRequiredMixin, ListView):
    template_name = "tasks/../../templates/common/deploy-location.html"
    context_object_name = "missions"

    def get_queryset(self):
        self.location_key = self.kwargs["location"]
        if self.location_key not in LOCATIONS:
            raise Http404
        return (
            missions_at(self.request.user, self.location_key)
            .annotate(has_due_chores=has_due_chores(), **item_progress())
            .order_by(F("due_date").asc(nulls_last=True), "-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_location_context())
        return context

    def get_location_context(self):
        location = LOCATIONS[self.location_key]
        return {
            "location_key": self.location_key,
            "location_label": location["label"],
            "groups": group_by_urgency(self.object_list),
        }