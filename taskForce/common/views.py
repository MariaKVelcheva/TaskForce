from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q, Exists, OuterRef, Count
from django.shortcuts import render, redirect
from django.views.generic import TemplateView

from taskForce.comms.models import Message, MessageRead
from taskForce.tasks.forms import QuickCreateTaskForm
from taskForce.tasks.models import Task
from taskForce.units.models import Unit

TaskUser = get_user_model()


class IndexView(TemplateView):
    template_name = "common/index.html"


class DebriefHomeView(LoginRequiredMixin, TemplateView):
    template_name = "common/debrief-home.html"

    RECENT_MESSAGES = 5
    VISIBLE_UNITS = 4

    def post(self, request, *args, **kwargs):
        form = QuickCreateTaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
        else:
            for error in form.errors.get("name", []):
                messages.error(request, error)

        return redirect(request.path)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = QuickCreateTaskForm()

        context.update(self.get_task_context())
        context.update(self.get_unit_context())
        context.update(self.get_message_context())

        avatar = getattr(self.request.user, "avatar", None)
        context["points"] = avatar.points if avatar else 0

        return context

    def get_task_context(self):
        tasks = Task.objects.filter(user=self.request.user)
        counts = tasks.aggregate(
            open=Count("pk", filter=Q(is_done=False)),
            done=Count("pk", filter=Q(is_done=True)),
        )
        return {
            "open_tasks": tasks.filter(is_done=False),
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
        read = MessageRead.objects.filter(message=OuterRef("pk"), user=user)

        visible = (
            Message.objects.filter(Q(sender=user) | Q(recipients=user))
            .annotate(is_read=Exists(read))
            .distinct().select_related("sender")
        )

        return {
            "recent_messages": visible.order_by("-created_at")[:self.RECENT_MESSAGES],
        }


