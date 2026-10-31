from taskForce.tasks.mixins import CheckableItem, checkable_constraints
from taskForce.tasks.models import TaskItem


class ListItem(CheckableItem, TaskItem):
    class Meta(TaskItem.Meta):
        constraints = checkable_constraints("listitem")

