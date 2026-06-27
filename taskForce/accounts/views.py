from urllib.parse import urlparse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model, login, logout
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView

from taskForce.accounts.forms import RegisterForm, LoginCustomForm, AvatarUpdateForm
from taskForce.accounts.models import Avatar

TaskUser = get_user_model()


class RegisterUserView(CreateView):
    model = TaskUser
    form_class = RegisterForm
    template_name = "accounts/register.html"

    def get_success_url(self):
        next_url = self.request.GET.get("next")

        if next_url:
            parsed_next = urlparse(next_url)
            if parsed_next.netloc == "":
                return next_url

        return reverse_lazy("home")

    def form_valid(self, form):
        """to do: add an email verification later, and a possibility to register through google and others"""
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return HttpResponseRedirect(self.get_success_url())


class LoginUserView(LoginView):
    form_class = LoginCustomForm
    template_name = "accounts/login.html"


class LogoutUserView(LoginRequiredMixin, LogoutView):
    next_page = reverse_lazy("home")


class DeleteUserView(LoginRequiredMixin, DeleteView):
    model = TaskUser
    template_name = "accounts/delete-user.html"
    success_url = reverse_lazy("home")

    def delete(self, request, *args, **kwargs):
        user = request.user
        logout(request)
        user.delete()
        return HttpResponseRedirect(self.get_success_url())

    def get_object(self, queryset=None):
        return self.request.user


class UpdateAvatarView(LoginRequiredMixin, UpdateView):
    model = Avatar
    form_class = AvatarUpdateForm
    template_name = "accounts/update-profile.html"
    success_url = reverse_lazy("profile-details")

    def get_object(self, queryset=None):
        return self.request.user


class ProfileDetailsView(LoginRequiredMixin, DetailView):
    model = Avatar
    template_name = "accounts/details-profile.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        return self.request.user
