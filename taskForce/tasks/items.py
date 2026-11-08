from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from taskForce.tasks.forms import (
    ChoreItemForm, GroceryItemForm, ListItemForm, PantryItemForm, WorkoutItemForm,
)
from taskForce.tasks.mixins import CheckableItem
from taskForce.tasks.models import (
    ChoreItem, GroceryItem, ListItem, PantryItem, TaskType, WorkoutItem,
)

ITEM_MODELS = {
    TaskType.GROCERIES: GroceryItem,
    TaskType.PANTRY: PantryItem,
    TaskType.WORKOUT: WorkoutItem,
    TaskType.CHORES: ChoreItem,
    TaskType.LIST: ListItem,
}

ITEM_FORMS = {
    TaskType.GROCERIES: GroceryItemForm,
    TaskType.PANTRY: PantryItemForm,
    TaskType.WORKOUT: WorkoutItemForm,
    TaskType.CHORES: ChoreItemForm,
    TaskType.LIST: ListItemForm,
}

ITEM_PARTIALS = {
    TaskType.GROCERIES: "tasks/partials/_supplies.html",
    TaskType.PANTRY: "tasks/partials/_pantry.html",
    TaskType.WORKOUT: "tasks/partials/_workouts.html",
    TaskType.CHORES: "tasks/partials/_chores.html",
    TaskType.LIST: "tasks/partials/_list.html",
}


def get_item_context(task):
    item_model = ITEM_MODELS.get(task.type)
    if item_model is None:
        return {"items": None}

    items = list(item_model.objects.filter(task=task))
    checkable = issubclass(item_model, CheckableItem)

    return {
        "items": items,
        "item_form": ITEM_FORMS[task.type](),
        "items_done": sum(1 for item in items if item.is_done) if checkable else None,
        "items_total": len(items),
        "item_partial": ITEM_PARTIALS[task.type],
        "task": task,
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


def item_progress(now=None):
    total = done = Value(0)
    for model in ITEM_MODELS.values():
        if not issubclass(model, CheckableItem):
            continue
        total = total + _count_items(model.objects.all())
        done = done + _count_items(model.objects.done(now))
    return {
        "items_total": total,
        "items_done": done,
        "duties_due": _count_items(ChoreItem.objects.due(now)),
        "stock_low": _count_items(PantryItem.objects.low()),
    }

