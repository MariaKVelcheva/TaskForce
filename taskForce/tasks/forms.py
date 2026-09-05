from django import forms
from django.contrib.auth import get_user_model

from taskForce.tasks.models import Task
from taskForce.units.models import Unit


User = get_user_model()


class BaseTaskForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit"].queryset = Unit.objects.filter(users=user)
        self.fields["assigned_to"].queryset = User.objects.filter(
            units__users=user
        ).distinct()

    class Meta:
        model = Task
        exclude = ['user', 'created_at', 'accomplished_at']

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
        exclude = BaseTaskForm.Meta.exclude + ["is_done", "assigned_to"]


class QuickCreateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("name", )


class UpdateTaskForm(BaseTaskForm):
    pass

