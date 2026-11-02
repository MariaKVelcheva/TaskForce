from django.db.models import Count, F, OuterRef, Q, Subquery

from taskForce.comms.models import Conversation, ConversationRead, Message
from taskForce.tasks.models import ChoreItem, PantryItem, Task, TaskType
from taskForce.units.models import Unit
from taskForce.units.services import active_unit_for


def unread_count(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user

    my_read = ConversationRead.objects.filter(
        conversation=OuterRef("conversation"),
        user=user,
    ).values("last_read_at")[:1]

    count = (
        Message.objects.filter(conversation__in=Conversation.objects.visible_to(user))
        .exclude(sender=user)
        .annotate(last_read_at=Subquery(my_read))
        .filter(Q(last_read_at__isnull=True) | Q(created_at__gt=F("last_read_at")))
        .values("conversation")
        .distinct()
        .count()
    )

    return {"unread_count": count}


def task_type_counts(request):
    if not request.user.is_authenticated:
        return {}

    active_tasks = Task.objects.visible_to(request.user).filter(is_active=True)

    counts = dict(
        active_tasks
        .order_by()
        .values_list("type")
        .annotate(total=Count("pk"))
    )

    attention_types = set(
        ChoreItem.objects.due()
        .filter(task__in=active_tasks)
        .order_by()
        .values_list("task__type", flat=True)
    ) | set(
        PantryItem.objects.low()
        .filter(task__in=active_tasks)
        .order_by()
        .values_list("task__type", flat=True)
    )

    type_nav = [
        {
            "value": "none" if value == TaskType.ONEOFF else value,
            "label": label,
            "count": counts[value],
            "attention": value in attention_types,
        }
        for value, label in TaskType.choices
        if counts.get(value)
    ]

    return {
        "type_nav": type_nav,
        "unsorted_count": counts.get(TaskType.ONEOFF, 0),
        "any_attention": bool(attention_types),
    }


def active_unit(request):
    if not request.user.is_authenticated:
        return {}

    unit = active_unit_for(request.user)
    others = list(
        Unit.objects.filter(memberships__user=request.user)
        .exclude(pk=unit.pk)
        .order_by("name")[:4]
    )
    return {
        "active_unit": unit,
        "switch_units": others[:3],
        "more_units": len(others) > 3,
    }


