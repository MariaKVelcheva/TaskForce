from django.contrib import admin
from taskForce.comms.models import Message, Conversation, ConversationRead


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "conversation", "created_at")
    list_filter = ("created_at",)
    search_fields = ("sender__username", "text")
    raw_id_fields = ("conversation", "sender")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "unit", "task", "created_at")
    list_filter = ("created_at",)
    raw_id_fields = ("unit", "task")


@admin.register(ConversationRead)
class ConversationReadAdmin(admin.ModelAdmin):
    list_display = ("user", "conversation", "last_read_at")
    raw_id_fields = ("user", "conversation")