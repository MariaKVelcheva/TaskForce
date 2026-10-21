from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone

from taskForce.tasks.models import Task, ChoreItem


def _hq(now):
    return Q(type__isnull=True) | Q(type="")


def _of_type(task_type):
    def _filter(now):
        return Q(type=task_type)
    return _filter


LOCATIONS = {
    "hq":       {"label": "HQ",              "filter": _hq},
    "training": {"label": "Training Ground", "filter": _of_type("workout")},
    "supply":   {"label": "Supply",          "filter": _of_type("groceries")},
    "barracks": {"label": "Barracks",        "filter": _of_type("chores")},
    "rec_room": {"label": "Rec Room",        "filter": _of_type("list")},
}


def missions_at(user, key, now=None):
    now = now or timezone.now()
    q = LOCATIONS[key]["filter"](now)
    return Task.objects.visible_to(user).filter(q, is_done=False)


def location_summary(user, now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)

    due_chores = ChoreItem.objects.due().filter(task=OuterRef("pk"))
    qs = (
        Task.objects.visible_to(user)
        .filter(is_done=False)
        .annotate(has_due_chores=Exists(due_chores))
        .order_by()
    )
    attention = Q(due_date__date__lte=today) | Q(has_due_chores=True)

    aggregates = {}
    for key, loc in LOCATIONS.items():
        q = loc["filter"](now)
        aggregates[f"{key}_count"] = Count("pk", filter=q, distinct=True)
        aggregates[f"{key}_attention"] = Count("pk", filter=q & attention, distinct=True)

    totals = qs.aggregate(**aggregates)
    return {
        key: {
            "count": totals[f"{key}_count"],
            "attention": totals[f"{key}_attention"] > 0,
        }
        for key in LOCATIONS
    }
