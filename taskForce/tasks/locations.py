from django.db.models import Q, Count, Exists, OuterRef, When, Value, Case, CharField
from django.utils import timezone

from taskForce.tasks.models import Task, ChoreItem
from taskForce.tasks.urgency import has_due_chores, bucket_for, BUCKETS, BUCKET_ORDER, urgency_key, ACTIONABLE


def _hq(now):
    return Q(type__isnull=True) | Q(type="")


def _of_type(task_type):
    def _filter(now):
        return Q(type=task_type)
    return _filter


LOCATIONS = {
    "hq": {"label": "HQ", "type": None, "filter": _hq},
    "training": {"label": "Training Ground", "type": "workout", "filter": _of_type("workout")},
    "supply": {"label": "Supply", "type": "groceries", "filter": _of_type("groceries")},
    "barracks": {"label": "Barracks", "type": "chores", "filter": _of_type("chores")},
    "rec_room": {"label": "Rec Room", "type": "list", "filter": _of_type("list")},
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
        .annotate(has_due_chores)
        .order_by()
    )

    STATES = {
        "overdue":   Q(due_date__lt=now) | Q(has_due_chores=True),
        "critical":  Q(priority=1),
        "due_today": Q(due_date__gte=now, due_date__date=today),
    }

    aggregates = {}
    for key, loc in LOCATIONS.items():
        q = loc["filter"](now)
        aggregates[f"{key}__count"] = Count("pk", filter=q, distinct=True)
        for state, state_q in STATES.items():
            aggregates[f"{key}__{state}"] = Count("pk", filter=q & state_q, distinct=True)

    totals = qs.aggregate(**aggregates)
    return {
        key: {
            "count": totals[f"{key}__count"],
            **{state: totals[f"{key}__{state}"] > 0 for state in STATES},
        }
        for key in LOCATIONS
    }


def location_previews(user, limit=3, now=None):
    now = now or timezone.now()
    whens = [When(loc["filter"](now), then=Value(key)) for key, loc in LOCATIONS.items()]
    missions = (
        Task.objects.visible_to(user)
        .filter(is_done=False)
        .annotate(
            location=Case(*whens, default=Value(None), output_field=CharField()),
            has_due_chores=has_due_chores(),
        )
    )

    for m in missions:
        m.bucket = bucket_for(m, now)

    ranked = sorted(missions, key=lambda m: urgency_key(m, now))
    previews = {key: [] for key in LOCATIONS}
    for m in ranked:
        if m.location and len(previews[m.location]) < limit:
            previews[m.location].append(m)
    return previews


def next_objective(previews, now):
    candidates = [
        (urgency_key(missions[0], now), key)
        for key, missions in previews.items()
        if missions and missions[0].bucket in ACTIONABLE
    ]
    return min(candidates)[1] if candidates else None