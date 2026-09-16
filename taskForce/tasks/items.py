from taskForce.tasks.forms import GroceryItemForm
from taskForce.tasks.models import GroceryItem

ITEM_MODELS = {
    "groceries": GroceryItem,
}


ITEM_FORMS = {
    "groceries": GroceryItemForm,
}