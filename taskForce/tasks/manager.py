from django.db import models
from django.db.models import Q, F, ExpressionWrapper, DateTimeField, Case, When, Value
from django.db.models.functions import Now
from datetime import timedelta


class TaskManager(models.Manager):
    def open_tasks(self):
        return self.filter(is_done=False).order_by("-created_at")

    def visible_to(self, user):
        return self.filter(Q(user=user) | Q(unit__users=user)).distinct().select_related("unit", "assigned_to", "user")


class TaskItemManager(models.Manager):
    def with_due_state(self):
        return self.get_queryset()


class ChoreItemManager(TaskItemManager):
    def with_due_state(self):
        due_at = ExpressionWrapper(
            F("last_done_at") + timedelta(days=1) * F("frequency_days"),
            output_field=DateTimeField(),
        )

        return self.annotate(
            due_at=due_at,
        ).annotate(
            is_due=Q(frequency_days__isnull=False)
            & (Q(last_done_at__isnull=True) | Q(due_at__lte=Now()))
        )