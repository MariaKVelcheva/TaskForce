from taskForce.tasks.forms import GroceryItemForm, WorkoutItemForm
from taskForce.tasks.models import GroceryItem, WorkoutItem

ITEM_MODELS = {
    "groceries": GroceryItem,
    "workout": WorkoutItem,
}


ITEM_FORMS = {
    "groceries": GroceryItemForm,
    "workout": WorkoutItemForm,
}


ITEM_PARTIALS = {
    "groceries": "tasks/partials/_supplies.html",
    "workout": "tasks/partials/_workouts.html",
}