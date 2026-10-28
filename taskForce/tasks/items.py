from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from taskForce.tasks.forms import GroceryItemForm, WorkoutItemForm, ChoreItemForm, ListItemForm
from taskForce.tasks.models import GroceryItem, WorkoutItem, ChoreItem, ListItem

ITEM_MODELS = {
    "groceries": GroceryItem,
    "workout": WorkoutItem,
    "chores": ChoreItem,
    "list": ListItem,
}


ITEM_FORMS = {
    "groceries": GroceryItemForm,
    "workout": WorkoutItemForm,
    "chores": ChoreItemForm,
    "list": ListItemForm,
}


ITEM_PARTIALS = {
    "groceries": "tasks/partials/_supplies.html",
    "workout": "tasks/partials/_workouts.html",
    "chores": "tasks/partials/_chores.html",
    "list": "tasks/partials/_list.html",
}


def _count_items(queryset):
    counts = (
        queryset.filter(task=OuterRef("pk"))
        .order_by()
        .values("task")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return Coalesce(Subquery(counts, output_field=IntegerField()), Value(0))


def item_progress():
    total = done = Value(0)
    for model in ITEM_MODELS.values():
        total = total + _count_items(model.objects.all())
        done = done + _count_items(model.objects.filter(is_done=True))
    return {
        "items_total": total,
        "items_done": done,
        "duties_due": _count_items(ChoreItem.objects.due()),
    }