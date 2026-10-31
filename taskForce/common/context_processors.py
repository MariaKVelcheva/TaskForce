from datetime import timedelta

from django.db.models import OuterRef, Subquery, Q, F, Count
from django.utils import timezone

from taskForce.comms.models import Message, ConversationRead
from taskForce.tasks.models import Task, ChoreItem


def unread_count(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user

    my_read = ConversationRead.objects.filter(
        conversation=OuterRef("conversation"),
        user=user,
    ).values("last_read_at")[:1]

    count = (
        Message.objects.filter(conversation__unit__memberships__user=user)
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

    visible_tasks = Task.objects.visible_to(request.user)

    counts: dict[str | None, int] = dict(
        visible_tasks
        .filter(is_active=True)
        .order_by()
        .values_list("type")
        .annotate(total=Count("pk", distinct=True))
    )

    due_types = set(
        ChoreItem.objects.due()
        .filter(task__in=visible_tasks, task__is_active=True)
        .values_list("task__type", flat=True)
    )

    labels = dict(Task.PRIORITY_CHOICES)

    type_nav = [
        {
            "value": value,
            "label": labels[value],
            "count": counts[value],
            "attention": value in due_types,
        }
        for value in labels if counts.get(value)
    ]

    return {
        "type_nav": type_nav,
        "unsorted_count": counts.get(None, 0),
        "any_attention": bool(due_types),
    }