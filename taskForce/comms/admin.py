from django.contrib import admin
from taskForce.comms.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'created_at', )
    list_filter = ('created_at', )
    search_fields = ('sender__username', )
