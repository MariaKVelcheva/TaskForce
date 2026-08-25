from django import forms
from django.utils.translation import gettext_lazy as _

from taskForce.comms.models import Message


class MessageBaseForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("text",)
        labels = {
            "text": _("Comm"),
        }
        widgets = {
            "text": forms.Textarea(attrs={"rows": 4, "placeholder": _("Your comm here")}),
        }


class MessageCreateForm(MessageBaseForm):
    pass


class SearchMessageForm(forms.Form):
    query = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={"placeholder": _("Search comms...")}),
    )