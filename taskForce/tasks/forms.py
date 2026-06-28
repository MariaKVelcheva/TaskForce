from django import forms

from taskForce.tasks.models import Task


class BaseTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        exclude = ['user', 'created_at', 'accomplished_at']
        labels = {
            "name": "Name",
            "assigned_to": "Assigned to",
            "is_done": "Is done",
            "type": "Type",
            "zone": "Zone",
            "unit": "Unit",
            "appointed_points": "Appointed points",
            "due_date": "Due date",
            "alarm_at": "Alarm at",
            "timer_duration": "Timer duration",
            "timer_at": "Timer at",
        }

        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Task name"}),

        }


class CreateTaskForm(BaseTaskForm):
    class Meta(BaseTaskForm.Meta):
        exclude = BaseTaskForm.Meta.exclude + ["is_done", "assigned_to"]


class UpdateTaskForm(BaseTaskForm):
    pass

