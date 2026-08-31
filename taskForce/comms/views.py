import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, OuterRef, Exists, F, Subquery, Max, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView
from django.utils.translation import gettext_lazy as _
from taskForce.comms.forms import MessageCreateForm, SearchMessageForm
from taskForce.comms.models import Message, ConversationRead, Conversation
from taskForce.tasks.models import Task
from taskForce.units.models import Unit


class OpenUnitChatView(LoginRequiredMixin, View):
    def get(self, request, pk):
        unit = get_object_or_404(Unit, pk=pk, memberships__user=request.user)
        conversation = Conversation.objects.for_unit(unit)
        return redirect("conversation", pk=conversation.pk)


class OpenTaskChatView(LoginRequiredMixin, View):
    def get(self, request, pk):
        task = get_object_or_404(
            Task,
            pk=pk,
            unit__isnull=False,
            unit__memberships__user=request.user,
        )

        conversation = Conversation.objects.for_task(task)

        return redirect("conversation", pk=conversation.pk)


class ConversationView(LoginRequiredMixin, ListView):
    template_name = "messages/conversation.html"
    context_object_name = "messages_list"

    def get_conversation(self):
        return get_object_or_404(
            Conversation.objects.visible_to(self.request.user).select_related("unit", "task"),
            pk=self.kwargs["pk"])

    def get_queryset(self):
        return self.get_conversation().messages.select_related("sender")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = self.get_conversation()

        ConversationRead.objects.update_or_create(
            conversation=conversation,
            user=self.request.user,
        )

        context["conversation"] = conversation
        context["form"] = MessageCreateForm()
        return context

    def post(self, request, *args, **kwargs):
        conversation = self.get_conversation()
        form = MessageCreateForm(request.POST, request.FILES)

        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
        else:
            messages.error(request, _("Comm cannot be empty."))

        return redirect("conversation", pk=conversation.pk)


class InboxView(LoginRequiredMixin, ListView):
    template_name = "messages/inbox.html"
    context_object_name = "conversations"

    def get_queryset(self):
        user = self.request.user

        my_read = ConversationRead.objects.filter(
            conversation=OuterRef("pk"),
            user=user,
        ).values("last_read_at")[:1]

        unread = Message.objects.filter(
            conversation=OuterRef("pk"),
            created_at__gt=OuterRef("last_read_at"),
        ).exclude(sender=user)

        conversations = (
            Conversation.objects.filter(unit__memberships__user=user)
            .select_related("unit", "task")
            .annotate(
                last_read_at=Coalesce(Subquery(my_read), Value(datetime.datetime(1970,
                                                                                 1, 1,
                                                                                 tzinfo=datetime.timezone.utc))),
                last_message_at=Max("messages__created_at"),
                has_unread=Exists(unread),
            )
            .order_by(F("last_message_at").desc(nulls_last=True))
        )

        query = self.request.GET.get("query")

        if query:
            matching = Message.objects.filter(
                conversation=OuterRef("pk"),
                text__icontains=query,
            ).order_by("-created_at").values("text")[:1]

            conversations = conversations.filter(
                Q(messages__text__icontains=query)
                | Q(unit__name__icontains=query)
                | Q(task__name__icontains=query)
            ).annotate(match_preview=Subquery(matching)).distinct()

        return conversations

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = SearchMessageForm(self.request.GET or None)
        return context

