from django import forms
from django.utils.translation import gettext_lazy as _

from taskForce.units.models import Unit


class BaseUnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        exclude = ("users", "invite_code", "created_by", )

        labels = {
            "name": _("Name"),
        }

        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
            "invite_code": forms.TextInput(attrs={"placeholder": _("Invite Code")}),
        }


class CreateUnitForm(BaseUnitForm):
    pass


class UpdateUnitForm(BaseUnitForm):
    pass


class JoinUnitForm(forms.Form):
    invite_code = forms.UUIDField(
        label=_("Clearance code"),
    )

    def clean_invite_code(self):
        code = self.cleaned_data["invite_code"]

        try:
            self.unit = Unit.objects.get(invite_code=code)
        except Unit.DoesNotExist:
            raise forms.ValidationError(_("No unit matches this clearance code."))

        return code