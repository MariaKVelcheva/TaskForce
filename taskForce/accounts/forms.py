import zoneinfo

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from taskForce.accounts.models import Avatar

User = get_user_model()


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email")
        labels = {
            "username": _("Username"),
            "email": _("Email"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = _("Password")
        self.fields["password2"].label = _("Confirm password")

    def clean_username(self):
        username = super().clean_username()
        if "@" in username:
            raise forms.ValidationError(_("Usernames can't contain @."))
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This email already exists."))
        return email


class LoginCustomForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Username or email"),
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("Wrong credentials, operative. Try again."),
    }


def time_zone_choices():
    return [(tz, tz.replace("_", " ")) for tz in sorted(zoneinfo.available_timezones())]


class TimeZoneForm(forms.ModelForm):
    time_zone = forms.ChoiceField(
        choices=time_zone_choices,
        label=_("Time zone"),
    )

    class Meta:
        model = Avatar
        fields = ["time_zone"]


