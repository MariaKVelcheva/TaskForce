from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView

from taskForce.comms.models import Conversation, ConversationRead, Message
from taskForce.common.deploy_map import TILE, building_positions, find_path, map_rows, tiles
from taskForce.redirects import with_next
from taskForce.tasks.forms import LocationQuickAddForm, QuickCreateTaskForm
from taskForce.tasks.items import ITEM_MODELS, item_progress
from taskForce.tasks.locations import (
    LOCATIONS, location_previews, location_summary, missions_at, next_objective,
)
from taskForce.tasks.models import SINGLETON_TYPES, Task, TaskType
from taskForce.tasks.urgency import group_by_urgency, with_urgency
from taskForce.units.models import Membership, Unit
from taskForce.units.services import active_unit_for


class IndexView(TemplateView):
    template_name = "common/index.html"


class DebriefHomeView(LoginRequiredMixin, TemplateView):
    template_name = "common/debrief-home.html"

    RECENT_MESSAGES = 5
    VISIBLE_UNITS = 4
    VISIBLE_TASKS = 5
    VISIBLE_OVERDUE = 5

    def post(self, request, *args, **kwargs):
        form = QuickCreateTaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.unit = active_unit_for(request.user)
            task.type = TaskType.ONEOFF
            task.save()
            messages.success(request, _("Standing order added."))
        else:
            for error in form.errors.get("name", []):
                messages.error(request, error)

        return redirect(request.get_full_path())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        context.update(self.get_task_context())
        context.update(self.get_unit_context())
        context.update(self.get_message_context())
        context.update(self.get_overdue_context(now))
        context.update(self.get_soon_due_context(now))
        context["points"] = self.request.user.avatar.points

        return context

    def get_task_context(self):
        tasks = Task.objects.visible_to(self.request.user).exclude(type__in=SINGLETON_TYPES)
        counts = tasks.aggregate(
            open=Count("pk", filter=Q(is_active=True)),
            done=Count("pk", filter=Q(is_accomplished=True)),
        )
        return {
            "open_tasks": (
                tasks.filter(is_active=True)
                .order_by(F("due_date").asc(nulls_last=True), "-created_at")
                [:self.VISIBLE_TASKS]
            ),
            "open_tasks_count": counts["open"],
            "done_tasks_count": counts["done"],
        }

    def get_unit_context(self):
        member_count = (
            Membership.objects.filter(unit=OuterRef("pk"))
            .order_by()
            .values("unit")
            .annotate(n=Count("pk"))
            .values("n")
        )
        return {
            "units": (
                Unit.objects.filter(memberships__user=self.request.user)
                .annotate(user_count=Subquery(member_count))
                .order_by("name")[:self.VISIBLE_UNITS]
            )
        }

    def get_message_context(self):
        user = self.request.user
        last_read = ConversationRead.objects.filter(
            conversation=OuterRef("conversation"),
            user=user,
        ).values("last_read_at")[:1]

        return {
            "recent_messages": (
                Message.objects.filter(conversation__in=Conversation.objects.visible_to(user))
                .select_related("sender", "conversation", "conversation__unit", "conversation__task")
                .annotate(last_read_at=Subquery(last_read))
                .annotate(
                    is_unread=(Q(last_read_at__isnull=True) | Q(created_at__gt=F("last_read_at")))
                    & ~Q(sender=user)
                )
                .order_by("-created_at")[:self.RECENT_MESSAGES]
            )
        }

    def get_overdue_context(self, now):
        missions = with_urgency(
            Task.objects.visible_to(self.request.user).filter(is_active=True), now,
        )
        return {
            "overdue_tasks": (
                missions.filter(
                    Q(has_due_chores=True) | Q(has_low_stock=True) | Q(due_date__lt=now)
                )
                .order_by("priority", F("due_date").asc(nulls_last=True))
                [:self.VISIBLE_OVERDUE]
            )
        }

    def get_soon_due_context(self, now):
        horizon = now + timedelta(days=2)
        return {
            "due_tasks": (
                Task.objects.visible_to(self.request.user)
                .filter(is_active=True, due_date__gte=now, due_date__lte=horizon)
                .order_by("due_date")[:self.VISIBLE_OVERDUE]
            )
        }


def _off_limits(key, unit):
    return key == "training" and unit.personal_for_id is None


def _single_singleton_type(location):
    types = location["types"]
    if len(types) == 1 and types[0] in SINGLETON_TYPES:
        return types[0]
    return None


class DeployIndexView(LoginRequiredMixin, TemplateView):
    template_name = "common/deploy-index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_locations_context())
        return context

    def get_locations_context(self):
        now = timezone.now()
        unit = active_unit_for(self.request.user)
        summary = location_summary(unit, now=now)
        previews = location_previews(unit, now=now)
        objective = next_objective(previews, now)

        positions = building_positions()
        rows = map_rows()
        width, height = len(rows[0]) * TILE, len(rows) * TILE

        buildings = []
        for key, loc in LOCATIONS.items():
            col, row = positions[key]
            buildings.append({
                "key": key,
                "label": loc["label"],
                "x": col * TILE,
                "y": row * TILE,
                "preview": previews[key],
                "more": summary[key]["count"] - len(previews[key]),
                "px": (col * TILE + TILE / 2) / width * 100,
                "py": (row * TILE - 16) / height * 100,
                "below": row < 5,
                "off_limits": _off_limits(key, unit),
                **summary[key],
            })

        hq_col, hq_row = positions["hq"]
        avatar_tile = (hq_col + 1, hq_row)
        route = ""
        if objective and objective != "hq":
            path = find_path(positions["hq"], positions[objective])
            if len(path) > 2:
                walk = path[1:-1]
                route = " ".join(
                    f"{c * TILE + TILE // 2},{r * TILE + TILE // 2}" for c, r in walk
                )
                avatar_tile = walk[-1]

        return {
            "unit": unit,
            "tiles": list(tiles()),
            "buildings": buildings,
            "map_width": width,
            "map_height": height,
            "route": route,
            "avatar_x": avatar_tile[0] * TILE,
            "avatar_y": avatar_tile[1] * TILE - 16,
            "objective": objective and {
                "label": LOCATIONS[objective]["label"],
                "mission": previews[objective][0],
            },
        }


class DeployLocationView(LoginRequiredMixin, ListView):
    template_name = "common/deploy-location.html"
    context_object_name = "missions"

    def dispatch(self, request, *args, **kwargs):
        self.location_key = kwargs["location"]
        if self.location_key not in LOCATIONS:
            raise Http404
        self.location = LOCATIONS[self.location_key]
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        singleton_type = _single_singleton_type(self.location)
        if singleton_type:
            unit = active_unit_for(request.user)
            if not _off_limits(self.location_key, unit):
                task = unit.tasks.filter(type=singleton_type).first()
                if task:
                    return redirect(with_next(
                        reverse("details-task", args=[task.pk]), reverse("deploy"),
                    ))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        self.now = timezone.now()
        self.unit = active_unit_for(self.request.user)
        if _off_limits(self.location_key, self.unit):
            return Task.objects.none()
        return with_urgency(
            missions_at(self.unit, self.location_key), self.now,
        ).annotate(
            **item_progress(now=self.now),
        ).order_by(
            "priority", F("due_date").asc(nulls_last=True), "-created_at",
        )

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        creates = self.location["creates"]
        if creates is None or _off_limits(self.location_key, self.unit):
            raise Http404

        form = LocationQuickAddForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.unit = self.unit
            task.type = creates
            task.save()
            messages.success(request, _("Mission deployed."))
            if task.type in ITEM_MODELS:
                return redirect(with_next(
                    reverse("details-task", args=[task.pk]), request.get_full_path(),
                ))
            return redirect(request.get_full_path())
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_create = self.location["creates"] is not None
        context.update({
            "location_key": self.location_key,
            "location_label": self.location["label"],
            "unit": self.unit,
            "can_create": can_create,
            "off_limits": _off_limits(self.location_key, self.unit),
            "groups": group_by_urgency(self.object_list, self.now),
            "form": kwargs.get("form") or (LocationQuickAddForm() if can_create else None),
        })
        return context


