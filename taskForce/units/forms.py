from django import forms
from django.utils.translation import gettext_lazy as _

from taskForce.units.models import Unit


class BaseUnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        exclude = ("users", )

        labels = {
            "name": _("Name"),
            "invite_code": _("Invite Code"),
        }

        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
            "invite_code": forms.TextInput(attrs={"placeholder": _("Invite Code")}),
        }


class CreateUnitForm(BaseUnitForm):
    pass


class UpdateUnitForm(BaseUnitForm):
    pass

