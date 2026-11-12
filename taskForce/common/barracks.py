from django.urls import reverse

from taskForce.common.house_map import BARRACKS, ENTRANCE
from taskForce.common.map_context import map_context
from taskForce.tasks.items import ITEM_FORMS, get_item_context
from taskForce.tasks.models import ChoreItem
from taskForce.tasks.rooms import (
    GENERAL, most_urgent_room, room_key, room_keys, room_summary, room_value,
)


def _room_labels():
    return {room_key(value): label for value, label in ChoreItem._meta.get_field("room").choices}


def barracks_context(chores, now, requested_room=None):
    summary = room_summary(chores, now)
    urgent = most_urgent_room(summary)
    selected = requested_room if requested_room in summary else (urgent or GENERAL)

    positions = BARRACKS.place_positions()
    labels = _room_labels()
    tile = BARRACKS.tile
    base_url = reverse("deploy-location", args=["barracks"])

    rooms = []
    for key in room_keys():
        col, row = positions[key]
        rooms.append({
            "key": key,
            "label": labels[key],
            "x": col * tile,
            "y": row * tile,
            "url": f"{base_url}?room={key}#duties",
            "selected": key == selected,
            **summary[key],
        })

    panel = get_item_context(chores)
    items = [item for item in panel["items"] if room_key(item.room) == selected]
    panel.update({
        "items": items,
        "items_done": sum(1 for item in items if item.is_done),
        "items_total": len(items),
        "item_form": ITEM_FORMS[chores.type](initial={"room": room_value(selected)}),
    })

    start = BARRACKS.position_of(ENTRANCE)
    goal = positions[urgent] if urgent else None

    return {
        **map_context(BARRACKS, start, goal),
        "rooms": rooms,
        "selected_room": {"key": selected, "label": labels[selected]},
        "panel": panel,
    }

