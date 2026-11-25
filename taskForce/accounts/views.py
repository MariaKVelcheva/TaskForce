from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model, login, logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.utils.translation import gettext_lazy as _

from taskForce.accounts.forms import RegisterForm, LoginCustomForm, TimeZoneForm
from taskForce.accounts.models import Avatar
from taskForce.redirects import get_next
from taskForce.units.services import create_personal_unit, blocking_commands, commanded_by

TaskUser = get_user_model()


class RegisterUserView(CreateView):
    model = TaskUser
    form_class = RegisterForm
    template_name = "accounts/register.html"

    def get_success_url(self):
        return get_next(self.request) or reverse_lazy("index")

    def form_valid(self, form):
        with transaction.atomic():
            user = form.save()
            create_personal_unit(user)
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return HttpResponseRedirect(self.get_success_url())


class LoginUserView(LoginView):
    form_class = LoginCustomForm
    template_name = "accounts/login.html"


class LogoutUserView(LoginRequiredMixin, LogoutView):
    next_page = reverse_lazy("index")


class DeleteUserView(LoginRequiredMixin, DeleteView):
    model = TaskUser
    http_method_names = ["post"]
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        user = self.request.user

        if blocking_commands(user).exists():
            messages.error(self.request, _("Transfer command of your units before deleting your account."))
            return redirect("details-profile")

        with transaction.atomic():
            commanded_by(user).filter(personal_for__isnull=True).delete()
            user.delete()

        logout(self.request)
        return HttpResponseRedirect(self.get_success_url())

    def get_object(self, queryset=None):
        return self.request.user


class UpdateAvatarView(LoginRequiredMixin, UpdateView):
    model = Avatar
    form_class = TimeZoneForm
    template_name = "accounts/update-profile.html"
    success_url = reverse_lazy("details-profile")

    def get_object(self, queryset=None):
        return self.request.user.avatar


class ProfileDetailsView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/details-profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({
            "avatar": user.avatar,
            "units": user.units.order_by(F("personal_for").asc(nulls_last=True), "name"),
            "blocking_units": blocking_commands(user),
            "solo_units": commanded_by(user).filter(personal_for__isnull=True),
        })
        return context


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("details-profile")
    success_message = _("Password changed, operative.")



