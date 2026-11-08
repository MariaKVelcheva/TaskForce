from django.db.models import Case, CharField, Count, Q, Value, When
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import Task, TaskType
from taskForce.tasks.urgency import (
    CRITICAL, bucket_for, is_actionable, urgency_key, with_urgency,
)

LOCATIONS = {
    "hq": {"label": _("HQ"), "types": (TaskType.ONEOFF,), "creates": TaskType.ONEOFF},
    "training": {"label": _("Training Ground"), "types": (TaskType.WORKOUT,), "creates": None},
        "supply": {
        "label": _("Supply"),
        "types": (TaskType.PANTRY, TaskType.GROCERIES),
        "creates": None,
        "interior": "common/interiors/supply.html",
    },
    "barracks": {"label": _("Barracks"), "types": (TaskType.CHORES,), "creates": None},
    "rec_room": {"label": _("Rec Room"), "types": (TaskType.LIST,), "creates": TaskType.LIST},
}


def location_q(key):
    return Q(type__in=LOCATIONS[key]["types"])


def _active_missions(unit):
    return Task.objects.filter(unit=unit, is_active=True)


def missions_at(unit, key, now=None):
    return _active_missions(unit).filter(location_q(key))


def location_summary(unit, now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)

    states = {
        "overdue": Q(has_due_chores=True) | Q(has_low_stock=True) | Q(due_date__lt=now),
        "critical": Q(priority=CRITICAL),
        "due_today": Q(due_date__gte=now, due_date__date=today),
    }

    aggregates = {}
    for key in LOCATIONS:
        q = location_q(key)
        aggregates[f"{key}__count"] = Count("pk", filter=q)
        for state, state_q in states.items():
            aggregates[f"{key}__{state}"] = Count("pk", filter=q & state_q)

    totals = with_urgency(_active_missions(unit), now).order_by().aggregate(**aggregates)
    return {
        key: {
            "count": totals[f"{key}__count"],
            **{state: totals[f"{key}__{state}"] > 0 for state in states},
        }
        for key in LOCATIONS
    }


def location_previews(unit, limit=3, now=None):
    now = now or timezone.now()
    whens = [When(location_q(key), then=Value(key)) for key in LOCATIONS]
    missions = with_urgency(_active_missions(unit), now).annotate(
        location=Case(*whens, default=Value(None), output_field=CharField()),
    )

    for m in missions:
        m.bucket = bucket_for(m, now)

    previews = {key: [] for key in LOCATIONS}
    for m in sorted(missions, key=lambda m: urgency_key(m, now)):
        if m.location and len(previews[m.location]) < limit:
            previews[m.location].append(m)
    return previews


def next_objective(previews, now):
    candidates = [
        (urgency_key(missions[0], now), key)
        for key, missions in previews.items()
        if missions and is_actionable(missions[0])
    ]
    return min(candidates)[1] if candidates else None