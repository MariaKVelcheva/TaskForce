from django import forms
from django.utils.translation import gettext_lazy as _

from taskForce.comms.models import Message


class MessageBaseForm(forms.models.ModelForm):
    class Meta:
        model = Message
        fields = ("title", "text", "recipients", "unit", "related_task")
        labels = {
            "text": _("Comm"),
            "recipients": _("Mission partners"),
            "related_task": _("Related task"),
        }
        widgets = {
            "text": forms.Textarea(attrs={'cols': 80, 'rows': 4, "placeholder": _("Your comm here")}),
            "recipients": forms.CheckboxSelectMultiple(),
            "unit": forms.Select(),
        }


class MessageCreateForm(MessageBaseForm):
    pass


class SearchMessageForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': _("Search in messages...")}),
    )