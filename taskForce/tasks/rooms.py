"""Chore counts per room, for the barracks floor plan.

The floor plan names rooms by key ("kitchen", ..., "general"). ChoreItem.room
stores the Room value, where General is "" (an empty string can't be a sprite
id or a URL parameter), so "" is translated to "general" here, in one place.
"""

from django.db.models import Count

from taskForce.tasks.models import ChoreItem

GENERAL = "general"


def room_key(value):
    return value or GENERAL


def room_value(key):
    return "" if key == GENERAL else key


def room_keys():
    return [room_key(value) for value, _label in ChoreItem._meta.get_field("room").choices]


def _count_by_room(queryset):
    rows = queryset.order_by().values_list("room").annotate(n=Count("pk"))
    return {room_key(room): n for room, n in rows}


def room_summary(chores, now):
    items = ChoreItem.objects.filter(task=chores)
    totals = _count_by_room(items)
    due = _count_by_room(ChoreItem.objects.due(now).filter(task=chores))
    return {
        key: {"total": totals.get(key, 0), "due": due.get(key, 0)}
        for key in room_keys()
    }


def most_urgent_room(summary):
    best = max(summary, key=lambda key: summary[key]["due"], default=None)
    if best is None or summary[best]["due"] == 0:
        return None
    return best

