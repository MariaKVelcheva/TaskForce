from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import TemplateView

from taskForce.comms.models import Message, MessageRead
from taskForce.tasks.models import Task
from taskForce.units.models import Unit

TaskUser = get_user_model()


class IndexView(TemplateView):
    template_name = "common/index.html"


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "common/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        user_tasks = Task.objects.filter(user=user)
        open_tasks = user_tasks.filter(is_done=False)
        done_tasks = user_tasks.filter(is_done=True)

        units = Unit.objects.filter(
            memberships__user=user,
        )[:4]

        user_messages = Message.objects.filter(
            Q(sender=user) | Q(recipients=user)
        ).distinct().order_by("-created_at")

        read_ids = set(
            MessageRead.objects.filter(
                user=user
            ).values_list('message_id', flat=True)
        )

        unread_count = user_messages.filter(
            ~Q(sender=user)
        ).exclude(pk__in=read_ids).count()

        context["open_tasks"] = open_tasks
        context["user_tasks"] = user_tasks
        context["open_tasks_count"] = open_tasks.count()
        context["done_tasks_count"] = done_tasks.count()
        context["units"] = units
        context["recent_messages"] = user_messages[:5]
        context["read_message_ids"] = read_ids
        context["unread_count"] = unread_count

        return context



