from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from taskForce.accounts.models import Avatar


User = get_user_model()


class RegisterForm(UserCreationForm):
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(),
    )

    password2 = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

        labels = {
            'username': _('Username'),
            'email': _('Email'),
            'password1': _('Password'),
            'password2': _('Confirm password'),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("This email already exists."))

        return email


class AvatarBaseForm(forms.ModelForm):
    class Meta:
        model = Avatar
        exclude = ('user', 'points',)

        labels = {
            'species': _('Species'),
            'hair_color': _('Hair color'),
            'glasses': _('Glasses'),
            'attire': _('Attire'),
        }

        widgets = {
            'glasses': forms.CheckboxInput(),
            'species': forms.RadioSelect(),
            'hair_color': forms.RadioSelect(),
            'attire': forms.CheckboxSelectMultiple(),

        }


class AvatarUpdateForm(AvatarBaseForm):
    pass

class LoginCustomForm(AuthenticationForm):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(),
    )

    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(),
    )

