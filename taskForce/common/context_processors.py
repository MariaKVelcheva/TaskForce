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

    counts: dict[str | None, int] = dict(
        Task.objects.visible_to(request.user)
        .filter(is_done=False)
        .values_list("type")
        .annotate(total=Count("pk", distinct=True))
    )

    labels = dict(Task.TYPE_CHOICES)

    type_nav = [
        {"value": value, "label": labels[value], "count": counts[value]}
        for value in labels if counts.get(value)
    ]

    return {
        "type_nav": type_nav,
        "unsorted_count": counts.get(None, 0),
    }


def due_count(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    horizon = timezone.now() + timedelta(hours=48)

    missions = Task.objects.visible_to(user).filter(
        is_done=False,
        due_date__isnull=False,
        due_date__lte=horizon,
    ).count()

    chores = ChoreItem.objects.due().filter(
        task__in=Task.objects.visible_to(user)
    ).count()

    return {"due_count": missions + chores}



