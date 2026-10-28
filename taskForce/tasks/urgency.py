from datetime import timedelta

from django.db.models import Exists, OuterRef
from django.utils import timezone

from taskForce.tasks.models import ChoreItem

SOON = timedelta(days=2)

BUCKETS = (
    ("overdue", "Overdue"),
    ("today", "Today"),
    ("soon", "Next 48 hours"),
    ("later", "Later"),
    ("unscheduled", "No due date"),
)


def has_due_chores():
    return Exists(ChoreItem.objects.due().filter(task=OuterRef("pk")))


def bucket_for(task, now):
    if getattr(task, "has_due_chores", False):
        return "overdue"
    if task.due_date is None:
        return "unscheduled"
    if task.due_date < now:
        return "overdue"
    if timezone.localdate(task.due_date) == timezone.localdate(now):
        return "today"
    if task.due_date <= now + SOON:
        return "soon"
    return "later"


def group_by_urgency(tasks, now=None):
    now = now or timezone.now()
    groups = {key: [] for key, _ in BUCKETS}
    for task in tasks:
        groups[bucket_for(task, now)].append(task)
    return [(key, label, groups[key]) for key, label in BUCKETS if groups[key]]