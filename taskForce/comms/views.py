from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView

from taskForce.comms.forms import MessageCreateForm, SearchMessageForm
from taskForce.comms.models import Message


class CreateMessageView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageCreateForm
    template_name = "messages/create-message.html"

    def form_valid(self, form):
        form.instance.sender = self.request.user
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("chat-history", kwargs={"pk": self.object.pk})


class DeleteMessageView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "messages/delete-message.html"

    def get_success_url(self):
        return reverse_lazy("chat-history", kwargs={"pk": self.object.pk})


class DetailsMessageView(LoginRequiredMixin, DetailView):
    model = Message
    context_object_name = "message"
    template_name = "messages/details-message.html"


class AllMessagesView(LoginRequiredMixin, ListView, FormView):
    model = Message
    context_object_name = "messages"
    form_class = SearchMessageForm #what now?
    template_name = "messages/all-messages.html"


class ChatHistoryView(LoginRequiredMixin, ListView, FormView):
    model = Message
    context_object_name = "messages"
    form_class = SearchMessageForm
    template_name = "messages/chat-history.html"
