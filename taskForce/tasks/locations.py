from django.db.models import Q
from django.utils import timezone

from taskForce.tasks.models import Task


def _gate(now):
    return Q(type__isnull=True) | Q(type="")


def _of_type(task_type):
    def _filter(now):
        return Q(type=task_type)
    return _filter


LOCATIONS = {
    "gate":     {"label": "HQ",        "x": 50, "y": 88, "filter": _gate},
    "training": {"label": "Training Ground", "x": 20, "y": 30, "filter": _of_type("workout")},
    "supply":   {"label": "Supply",    "x": 80, "y": 30, "filter": _of_type("groceries")},
    "quarters": {"label": "Barracks",        "x": 25, "y": 62, "filter": _of_type("chores")},
    "rec_room": {"label": "Rec Room",        "x": 75, "y": 62, "filter": _of_type("list")},
}


def missions_at(user, key, now=None):
    now = now or timezone.now()
    q = LOCATIONS[key]["filter"](now)
    return Task.objects.visible_to(user).filter(q, is_done=False)