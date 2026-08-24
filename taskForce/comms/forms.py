from django import forms
from django.utils.translation import gettext_lazy as _

from taskForce.comms.models import Message


class MessageBaseForm(forms.models.ModelForm):
    class Meta:
        model = Message
        exclude = ("created_at", )
        labels = {
            "text": _("Comm"),
        }
        widgets = {
            "text": forms.Textarea(attrs={'cols': 80, 'rows': 4, "placeholder": _("Your comm here")}),
        }


class MessageCreateForm(MessageBaseForm):
    pass


class SearchMessageForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': _("Search in comms...")}),
    )

