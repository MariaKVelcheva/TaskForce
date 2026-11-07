from django.db import models, transaction
from django.db.models import CheckConstraint, F, Q, Value
from django.db.models.functions import Greatest
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.mixins import CheckableItem, RecurringItem, recurring_checkable_constraints
from taskForce.tasks.models import TaskItem


class GroceryItem(RecurringItem, CheckableItem, TaskItem):
    quantity = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("quantity"),
    )
    pantry_item = models.OneToOneField(
        to="tasks.PantryItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grocery_item",
        verbose_name=_("shelf product"),
    )
    amount = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("amount to buy"),
    )

    @property
    def is_linked(self):
        return self.pantry_item_id is not None

    def tick(self, user):
        with transaction.atomic():
            done = super().tick(user)
            if done and self.is_linked and self.amount:
                from taskForce.tasks.models import PantryItem

                PantryItem.objects.filter(pk=self.pantry_item_id).update(
                    quantity=F("quantity") + self.amount
                )
        return done

    def untick(self):
        with transaction.atomic():
            done = super().untick()
            if done and self.is_linked and self.amount:
                from taskForce.tasks.models import PantryItem

                PantryItem.objects.filter(pk=self.pantry_item_id).update(
                    quantity=Greatest(F("quantity") - self.amount, Value(0))
                )
        return done

    class Meta(TaskItem.Meta):
        constraints = recurring_checkable_constraints("groceryitem") + [
            CheckConstraint(
                condition=Q(pantry_item__isnull=True) | Q(frequency_days__isnull=True),
                name="groceryitem_linked_not_recurring",
            ),
        ]

