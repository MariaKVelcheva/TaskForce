from datetime import datetime, time, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import (
    SINGLETON_TYPES, ChoreItem, GroceryItem, ListItem, PantryItem, Task, TaskType, WorkoutItem,
)
from taskForce.units.models import Unit

User = get_user_model()
DEADLINE = time(23, 59)


def creatable_type_choices():
    return [
        (value, label)
        for value, label in TaskType.choices
        if value not in SINGLETON_TYPES
    ]


class BaseTaskForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        my_units = Unit.objects.filter(users=user)

        if "unit" in self.fields:
            self.fields["unit"].queryset = my_units

        if "assigned_to" in self.fields:
            if self.instance.unit_id:
                members = self.instance.unit.users.all()
            else:
                members = User.objects.filter(units__in=my_units).distinct()
            self.fields["assigned_to"].queryset = members

    def clean(self):
        cleaned = super().clean()
        unit = cleaned.get("unit") or (self.instance.unit if self.instance.unit_id else None)
        assigned_to = cleaned.get("assigned_to")
        if assigned_to and unit and not unit.users.filter(pk=assigned_to.pk).exists():
            raise forms.ValidationError(_("That operative is not in the selected unit."))
        return cleaned

    class Meta:
        model = Task
        fields = ["name", "type", "comment", "priority", "unit", "assigned_to"]

        labels = {
            "name": _("Mission name"),
            "assigned_to": _("Assign to operative"),
            "type": _("Type"),
            "unit": _("Unit"),
            "due_date": _("Due date"),
            "priority": _("Priority"),
            "comment": _("Comment"),
        }

        help_texts = {
            "comment": _("Notes about the mission itself. For discussion, use the mission chat."),
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": _("Describe the objective..."),
                "autofocus": True,
            }),
            "type": forms.Select(attrs={"class": "select-field"}),
            "priority": forms.Select(attrs={"class": "select-field"}),
            "comment": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": _("What is this mission about?"),
            }),
            "unit": forms.Select(attrs={"class": "select-field"}),
            "assigned_to": forms.Select(attrs={"class": "select-field"}),
            "due_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }


class CreateTaskForm(BaseTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = creatable_type_choices()

    class Meta(BaseTaskForm.Meta):
        fields = ["name", "priority", "type", "unit", "assigned_to", "due_date", "comment"]


class UpdateTaskForm(BaseTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.type not in (TaskType.ONEOFF, TaskType.LIST):
            del self.fields["due_date"]

    class Meta(BaseTaskForm.Meta):
        fields = ["name", "priority", "assigned_to", "due_date", "comment"]


class QuickCreateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Quick add a standing order...")}),
        }


class LocationQuickAddForm(forms.ModelForm):
    WHEN_CHOICES = (
        ("", _("No date")),
        ("today", _("Today")),
        ("tomorrow", _("Tomorrow")),
        ("pick", _("Pick date")),
    )
    when = forms.ChoiceField(
        choices=WHEN_CHOICES,
        required=False,
        widget=forms.RadioSelect,
        initial="",
    )

    class Meta:
        model = Task
        fields = ["name", "priority", "due_date"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("New mission…"), "autocomplete": "off"}),
            "priority": forms.RadioSelect,
            "due_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, now=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.now = now
        self.fields["due_date"].required = False

    def clean(self):
        cleaned = super().clean()
        when = cleaned.get("when")
        today = timezone.localdate(self.now or timezone.now())

        if when == "today":
            cleaned["due_date"] = self._deadline(today)
        elif when == "tomorrow":
            cleaned["due_date"] = self._deadline(today + timedelta(days=1))
        elif when == "pick":
            if not cleaned.get("due_date"):
                self.add_error("due_date", _("Pick a date and time."))
        else:
            cleaned["due_date"] = None
        return cleaned

    @staticmethod
    def _deadline(day):
        return timezone.make_aware(datetime.combine(day, DEADLINE))


class GroceryItemForm(forms.ModelForm):
    class Meta:
        model = GroceryItem
        fields = ("name", "quantity", "frequency_days")
        labels = {
            "name": _("Grocery item"),
            "quantity": _("Quantity"),
            "frequency_days": _("Buy every (days)"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Add supply...")}),
            "quantity": forms.TextInput(attrs={"placeholder": _("500g")}),
            "frequency_days": forms.NumberInput(attrs={"min": 1, "max": 365}),
        }


class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItem
        fields = ("name", "quantity", "threshold")
        labels = {
            "name": _("Product"),
            "quantity": _("In stock"),
            "threshold": _("Low at"),
        }
        help_texts = {
            "threshold": _("Flag the product when stock drops to this number or below."),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Add product...")}),
            "quantity": forms.NumberInput(attrs={"min": 0}),
            "threshold": forms.NumberInput(attrs={"min": 0}),
        }


class WorkoutItemForm(forms.ModelForm):
    class Meta:
        model = WorkoutItem
        fields = ("name", "reps", "duration", "weight")
        labels = {
            "name": _("Workout name"),
            "reps": _("Reps"),
            "duration": _("Duration"),
            "weight": _("Weight"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Add workout...")}),
            "reps": forms.TextInput(attrs={"placeholder": _("8 reps")}),
            "weight": forms.TextInput(attrs={"placeholder": _("10 kgs")}),
        }


class ChoreItemForm(forms.ModelForm):
    class Meta:
        model = ChoreItem
        fields = ("name", "minutes", "frequency_days", "room")
        labels = {
            "name": _("Duty name"),
            "minutes": _("Minutes"),
            "frequency_days": _("Repeat every (days)"),
            "room": _("Sector"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Add duty...")}),
            "minutes": forms.NumberInput(attrs={"min": 1, "max": 480}),
            "frequency_days": forms.NumberInput(attrs={"min": 1, "max": 365}),
            "room": forms.Select(attrs={"class": "item-add-room"}),
        }


class ListItemForm(forms.ModelForm):
    class Meta:
        model = ListItem
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Add entry...")}),
        }


