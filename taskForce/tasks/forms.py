from django import forms
from django.contrib.auth import get_user_model

from taskForce.tasks.models import Task
from taskForce.units.models import Unit


User = get_user_model()


class BaseTaskForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if "unit" in self.fields:
            self.fields["unit"].queryset = Unit.objects.filter(users=user)

        if "assigned_to" in self.fields:
            self.fields["assigned_to"].queryset = User.objects.filter(
                units__in=Unit.objects.filter(users=user)
            ).distinct()

    def clean(self):
        cleaned = super().clean()
        unit = cleaned.get("unit")
        assigned_to = cleaned.get("assigned_to")
        if assigned_to and not unit:
            raise forms.ValidationError("Assign a unit before assigning an operative.")
        if assigned_to and unit and not unit.users.filter(pk=assigned_to.pk).exists():
            raise forms.ValidationError("That operative is not in the selected unit.")
        return cleaned

    class Meta:
        model = Task
        fields = ["name", "type", "unit", "assigned_to", "appointed_points", "due_date", "is_done"]

        labels = {
            "name": "Mission name",
            "assigned_to": "Assign to operative",
            "is_done": "Already complete",
            "type": "Type",
            "unit": "Unit",
            "appointed_points": "Intel points",
            "due_date": "Due date",
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Describe the objective...",
                "autofocus": True,
            }),
            "type": forms.Select(attrs={
                "class": "select-field",
            }),
            "unit": forms.Select(attrs={
                "class": "select-field",
            }),
            "assigned_to": forms.Select(attrs={
                "class": "select-field",
            }),
            "appointed_points": forms.NumberInput(attrs={
                "min": 0,
                "max": 100,
                "step": 1,
            }),
            "due_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "is_done": forms.CheckboxInput(attrs={
                "class": "checkbox-field",
            }),
        }


class CreateTaskForm(BaseTaskForm):
    class Meta(BaseTaskForm.Meta):
        fields = ["name", "type", "unit", "appointed_points", "due_date"]


class QuickCreateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("name", )


class UpdateTaskForm(BaseTaskForm):
    class Meta(BaseTaskForm.Meta):
        fields = ["name", "type", "appointed_points", "due_date"]

