from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model, login, logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView
from django.utils.translation import gettext_lazy as _

from taskForce.accounts.forms import RegisterForm, LoginCustomForm, TimeZoneForm
from taskForce.accounts.models import Avatar
from taskForce.redirects import get_next
from taskForce.units.services import create_personal_unit, blocking_commands

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
    template_name = "accounts/delete-user.html"
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        user = self.request.user
        logout(self.request)

        if blocking_commands(user).exists():
            messages.error(self.request, _("Transfer command of your units before deleting your account."))
            return redirect("all-units")

        user.delete()
        return HttpResponseRedirect(self.get_success_url())

    def get_object(self, queryset=None):
        return self.request.user


class UpdateAvatarView(LoginRequiredMixin, UpdateView):
    model = Avatar
    form_class = TimeZoneForm
    template_name = "accounts/update-profile.html"
    success_url = reverse_lazy("profile-details")

    def get_object(self, queryset=None):
        return self.request.user.avatar


class ProfileDetailsView(LoginRequiredMixin, DetailView):
    model = Avatar
    template_name = "accounts/details-profile.html"
    context_object_name = "profile"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        avatar = getattr(self.request.user, "avatar", None)
        context["points"] = avatar.points if avatar else 0
        return context

    def get_object(self, queryset=None):
        return self.request.user
