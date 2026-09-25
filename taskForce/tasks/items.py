from taskForce.tasks.forms import GroceryItemForm, WorkoutItemForm
from taskForce.tasks.models import GroceryItem, WorkoutItem

ITEM_MODELS = {
    "groceries": GroceryItem,
    "workouts": WorkoutItem,
}


ITEM_FORMS = {
    "groceries": GroceryItemForm,
    "workouts": WorkoutItemForm,
}