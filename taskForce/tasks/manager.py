from datetime import timedelta

from django.db import models
from django.db.models import Q, F
from django.utils import timezone


class TaskManager(models.Manager):
    def open_tasks(self):
        return self.filter(is_done=False).order_by("-created_at")

    def visible_to(self, user):
        return self.filter(Q(user=user) | Q(unit__users=user)).distinct().select_related("unit", "assigned_to", "user")


class ChoreItemManager(models.Manager):
    def with_due_date(self):
        return self.annotate(
            is_due=Q(last_done_at__isnull=True)
            | Q(last_done_at__lte=timezone.now() - F("frequency_days") * timedelta(days=1))
        )