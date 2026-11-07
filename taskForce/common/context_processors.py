from django.db.models import Count, F, OuterRef, Q, Subquery
from django.urls import reverse

from taskForce.comms.models import Conversation, ConversationRead, Message
from taskForce.tasks.models import SINGLETON_TYPES, ChoreItem, PantryItem, Task, TaskType
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

    user = request.user
    active_tasks = Task.objects.visible_to(user).filter(is_active=True)

    counts = dict(
        active_tasks
        .order_by()
        .values_list("type")
        .annotate(total=Count("pk"))
    )

    flagged = set(
        ChoreItem.objects.due()
        .filter(task__in=active_tasks)
        .order_by()
        .values_list("task_id", "task__type")
    ) | set(
        PantryItem.objects.low()
        .filter(task__in=active_tasks)
        .order_by()
        .values_list("task_id", "task__type")
    )
    flagged_tasks = {task_id for task_id, _type in flagged}
    flagged_types = {task_type for _id, task_type in flagged}

    unit = active_unit_for(user)
    singletons = dict(
        unit.tasks.filter(type__in=SINGLETON_TYPES).order_by().values_list("type", "pk")
    )
    
    if TaskType.WORKOUT not in singletons:
        workout = (
            user.personal_unit.tasks.filter(type=TaskType.WORKOUT)
            .values_list("pk", flat=True).first()
        )
        if workout:
            singletons[TaskType.WORKOUT] = workout

    log_url = reverse("all-tasks")
    type_nav = []
    for value, label in TaskType.choices:
        if value in singletons:
            pk = singletons[value]
            type_nav.append({
                "value": value,
                "label": label,
                "url": reverse("details-task", args=[pk]),
                "count": None,
                "attention": pk in flagged_tasks,
            })
        elif counts.get(value):
            token = "none" if value == TaskType.ONEOFF else value
            type_nav.append({
                "value": token,
                "label": label,
                "url": f"{log_url}?type={token}",
                "count": counts[value],
                "attention": value in flagged_types,
            })

    return {
        "type_nav": type_nav,
        "unsorted_count": counts.get(TaskType.ONEOFF, 0),
        "any_attention": bool(flagged),
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

