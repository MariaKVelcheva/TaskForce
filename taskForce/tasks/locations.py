from django.db.models import Q
from django.utils import timezone

from taskForce.tasks.models import Task


def _gate(now):
    today = timezone.localdate(now)
    untyped = Q(type__isnull=True) | Q(type="")
    due = Q(due_date__date__lte=today)
    return untyped | due


LOCATIONS = {
    "gate": {"label": "Gate", "x": 50, "y": 88, "filter": _gate},
}


def missions_at(user, key, now=None):
    now = now or timezone.now()
    q = LOCATIONS[key]["filter"](now)
    return Task.objects.visible_to(user).filter(q, is_done=False)