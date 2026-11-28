import math
from collections import defaultdict

from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import ChoreItem, Room

GENERAL = "general"

DEFAULT_ROOMS = (_("Kitchen"), _("Bathroom"), _("Bedroom"), _("Living room"), _("Outdoor"))


def create_default_rooms(chores):
    Room.objects.bulk_create([
        Room(task=chores, name=str(name), position=position)
        for position, name in enumerate(DEFAULT_ROOMS)
    ])


def _days_until_due(item, now):
    due_at = item.next_due_at
    if due_at is None or due_at <= now:
        return None
    return math.ceil((due_at - now).total_seconds() / 86400)


def room_cards(chores, now):
    rooms = list(Room.objects.filter(task=chores))
    duties_by_room = defaultdict(list)
    for item in ChoreItem.objects.filter(task=chores):
        item.due_in_days = _days_until_due(item, now)
        duties_by_room[item.room_id].append(item)

    cards = []
    for number, room in enumerate([*rooms, None], start=1):
        duties = sorted(duties_by_room.get(room.pk if room else None, []), key=lambda i: i.is_done)
        cards.append({
            "room": room,
            "key": str(room.pk) if room else GENERAL,
            "code": f"RM-{number:02d}" if room else "GEN",
            "label": room.name if room else _("General"),
            "duties": duties,
            "due": sum(1 for item in duties if not item.is_done),
            "total": len(duties),
        })
    return cards

