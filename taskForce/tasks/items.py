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

