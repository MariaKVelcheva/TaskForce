from django.utils import timezone

from taskForce.tasks.exercises import library_names
from taskForce.tasks.forms import WorkoutItemForm
from taskForce.tasks.managers import week_date
from taskForce.tasks.models import WorkoutItem


def planner_context(workout, user):
    today = timezone.localdate()
    items = list(WorkoutItem.objects.filter(task=workout).select_related("exercise"))

    days = []
    for weekday, label in WorkoutItem.Weekday.choices:
        day_items = [item for item in items if item.weekday == weekday]
        date = week_date(weekday, today)
        days.append({
            "weekday": weekday,
            "label": label,
            "date": date,
            "is_today": date == today,
            "is_past": date < today,
            "items": day_items,
            "done": sum(1 for item in day_items if item.is_done),
            "total": len(day_items),
        })

    return {
        "workout": workout,
        "days": days,
        "unplanned": [item for item in items if item.weekday is None],
        "weekdays": WorkoutItem.Weekday.choices,
        "suggestions": library_names(user),
        "item_form": WorkoutItemForm(),
    }

