from taskForce.tasks.forms import GroceryItemForm, WorkoutItemForm, ChoreItemForm
from taskForce.tasks.models import GroceryItem, WorkoutItem, ChoreItem

ITEM_MODELS = {
    "groceries": GroceryItem,
    "workout": WorkoutItem,
    "chores": ChoreItem,
}


ITEM_FORMS = {
    "groceries": GroceryItemForm,
    "workout": WorkoutItemForm,
    "chores": ChoreItemForm,
}


ITEM_PARTIALS = {
    "groceries": "tasks/partials/_supplies.html",
    "workout": "tasks/partials/_workouts.html",
    "chores": "tasks/partials/_chores.html",
}

