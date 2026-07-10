from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from taskForce.comms.forms import MessageCreateForm, SearchMessageForm
from taskForce.comms.models import Message, MessageRead
from taskForce.tasks.models import Task
from taskForce.units.models import Unit


class CreateMessageView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageCreateForm
    template_name = "messages/create-message.html"


    def form_valid(self, form):
        form.instance.sender = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.unit:
            return reverse_lazy("unit-chat", kwargs={"pk": self.object.unit.pk})
        if self.object.task:
            return reverse_lazy("task-thread", kwargs={"pk": self.object.related_task.pk})
        return reverse_lazy("inbox")


class DeleteMessageView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "messages/delete-message.html"

    def get_queryset(self):
        return Message.objects.filter(
            sender=self.request.user,
        )

    def get_success_url(self):
        return reverse_lazy("inbox")


class DetailsMessageView(LoginRequiredMixin, DetailView):
    model = Message
    context_object_name = "message"

    def get_queryset(self):
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(recipients=self.request.user),
        )

    def get_object(self, queryset=None):
        message = super().get_object(queryset)

        if message.sender != self.request.user:
            MessageRead.objects.get_or_create(
                message=message,
                user=self.request.user,
            )

        return message

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['read_message_ids'] = set(
            MessageRead.objects.filter(
                user=self.request.user,
            ).values_list('message_id', flat=True))
        return context


class InboxView(LoginRequiredMixin, ListView):
    model = Message
    context_object_name = "messages"
    template_name = "messages/inbox.html"

    def get_queryset(self):
        user = self.request.user

        messages = Message.objects.filter(
            Q(sender=user) | Q(recipients=user)
        ).distinct().order_by("-created_at")

        query = self.request.GET.get("query")

        if query:
            messages = messages.filter(
                Q(text__icontains=query) | Q(title__icontains=query) | Q(sender__username__icontains=query)
            )

        return messages

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = SearchMessageForm(self.request.GET or None)
        context['read_message_ids'] = set(
            MessageRead.objects.filter(
                user=self.request.user
            ).values_list('message_id', flat=True)
        )
        return context


class UnitChatView(LoginRequiredMixin, ListView):
    model = Message
    context_object_name = "messages"
    template_name = "messages/unit-chat.html"

    def get_queryset(self):
        messages = Message.objects.filter(
            unit__pk=self.kwargs["pk"],
            unit__memberships__user=self.request.user,
        ).order_by("created_at")

        query = self.request.GET.get("query")

        if query:
            messages = messages.filter(
                Q(text__icontains=query) | Q(title__icontains=query) | Q(sender__username__icontains=query)
            )

        return messages

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unit"] = get_object_or_404(Unit, pk=self.kwargs["pk"], memberships__user=self.request.user)
        context['search_form'] = SearchMessageForm(self.request.GET or None)
        context['read_message_ids'] = set(
            MessageRead.objects.filter(
                user=self.request.user,
            ).values_list('message_id', flat=True))
        return context


class ChatThreadView(LoginRequiredMixin, ListView):
    model = Message
    context_object_name = "messages"
    template_name = "messages/task-thread.html"

    def get_queryset(self):
        messages = Message.objects.filter(
            task__pk=self.kwargs["pk"],
        ).order_by("created_at")

        query = self.request.GET.get("query")

        if query:
            messages = messages.filter(
                Q(text__icontains=query) | Q(title__icontains=query) | Q(sender__username__icontains=query) |
                Q(related_task__name__icontains=query)
            )

        return messages

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = SearchMessageForm(self.request.GET or None)
        context["task"] = get_object_or_404(Task, pk=self.kwargs['pk'])
        return context

