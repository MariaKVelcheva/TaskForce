from datetime import timedelta

from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import ChoreItem, PantryItem

SOON = timedelta(days=2)
CRITICAL = 1

BUCKETS = (
    ("overdue", _("Action required")),
    ("today", _("Today")),
    ("soon", _("Next 48 hours")),
    ("later", _("Later")),
    ("unscheduled", _("No deadline")),
)

BUCKET_ORDER = {key: i for i, (key, _label) in enumerate(BUCKETS)}

ACTIONABLE = {"overdue", "today", "soon"}


def has_due_chores(now=None):
    return Exists(ChoreItem.objects.due(now).filter(task=OuterRef("pk")))


def has_low_stock():
    return Exists(PantryItem.objects.low().filter(task=OuterRef("pk")))


def with_urgency(queryset, now=None):
    return queryset.annotate(
        has_due_chores=has_due_chores(now),
        has_low_stock=has_low_stock(),
    )


def bucket_for(task, now):
    if getattr(task, "has_due_chores", False) or getattr(task, "has_low_stock", False):
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


def is_actionable(task):
    return task.bucket in ACTIONABLE or task.priority == CRITICAL


def urgency_key(task, now):
    return (
        not is_actionable(task),
        BUCKET_ORDER[task.bucket],
        task.priority,
        task.due_date or now,
    )


def group_by_urgency(tasks, now=None):
    now = now or timezone.now()
    groups = {key: [] for key, _label in BUCKETS}
    for task in tasks:
        groups[bucket_for(task, now)].append(task)
    return [(key, label, groups[key]) for key, label in BUCKETS if groups[key]]