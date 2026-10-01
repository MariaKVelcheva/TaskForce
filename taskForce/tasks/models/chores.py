from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.manager import ChoreItemManager
from taskForce.tasks.models import TaskItem


class ChoreItem(TaskItem):
    ROOM_CHOICES = (
        ("", "Section"),
        ("kitchen", _("Kitchen")),
        ("bathroom", _("Bathroom")),
        ("bedroom", _("Bedroom")),
        ("living", _("Living room")),
        ("outdoor", _("Outdoor")),
    )

    minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Minutes"),
    )

    room = models.CharField(
        max_length=100,
        blank=True,
        choices=ROOM_CHOICES,
        verbose_name=_("Room"),
    )

    frequency_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Frequency days"),
    )

    last_done_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last done at"),
    )

    objects = ChoreItemManager()

    def toggle(self):
        if not self.is_recurring:
            return super().toggle()

        with transaction.atomic():
            latest = self.completions.first()

            if latest and not self.is_due:
                latest.delete()
                remaining = self.completions.first()
                self.last_done_at = remaining.done_at if remaining else None
            else:
                completion = self.completions.create()
                self.last_done_at = completion.done_at

            self.save(update_fields=["last_done_at"])

    @property
    def is_recurring(self):
        return self.frequency_days is not None

    @property
    def is_satisfied(self):
        if not self.is_recurring:
            return self.is_done
        return not getattr(self, "is_due", True)


class ChoreCompletion(models.Model):
    chore_item = models.ForeignKey(
        to=ChoreItem,
        on_delete=models.CASCADE,
        verbose_name=_("Duty"),
        related_name="completions",
    )

    done_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ("-done_at", )