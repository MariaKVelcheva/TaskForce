from taskForce.tasks.rooms import room_cards


def barracks_context(chores, now):
    cards = room_cards(chores, now)
    return {
        "chores": chores,
        "cards": cards,
        "due_total": sum(card["due"] for card in cards),
        "due_rooms": sum(1 for card in cards if card["due"]),
    }

