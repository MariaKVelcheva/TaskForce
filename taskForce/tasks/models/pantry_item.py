from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.managers import PantryItemManager
from taskForce.tasks.models import TaskItem


class PantryItem(TaskItem):
    quantity = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("in stock"),
    )

    threshold = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("low at"),
    )

    objects = PantryItemManager()

    @property
    def is_low(self):
        return self.quantity <= self.threshold

    @property
    def restock_amount(self):
        return max(self.threshold + 1 - self.quantity, 1)

    def save(self, *args, **kwargs):
        created = self._state.adding
        super().save(*args, **kwargs)
        if created and self.is_low:
            self.put_on_list()

    def adjust(self, delta):
        with transaction.atomic():
            item = PantryItem.objects.select_for_update().get(pk=self.pk)
            was_low = item.is_low
            item.quantity = max(item.quantity + delta, 0)
            PantryItem.objects.filter(pk=item.pk).update(quantity=item.quantity)
            if item.is_low and not was_low:
                item.put_on_list()
        return item

    def put_on_list(self):
        from taskForce.tasks.models import GroceryItem, TaskType

        linked = GroceryItem.objects.filter(pantry_item=self).first()
        if linked is None:
            grocery_list = self.task.unit.tasks.get(type=TaskType.GROCERIES)
            GroceryItem.objects.create(
                task=grocery_list,
                name=self.name,
                pantry_item=self,
                amount=self.restock_amount,
            )
        elif linked.is_checked:
            GroceryItem.objects.filter(pk=linked.pk).update(
                is_checked=False,
                checked_by=None,
                amount=self.restock_amount,
            )

    class Meta(TaskItem.Meta):
        pass

