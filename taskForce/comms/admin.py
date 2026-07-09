from django.contrib import admin
from taskForce.comms.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'get_recipients', 'unit', 'task_name', 'created_at', )
    list_filter = ('unit', 'created_at', )
    search_fields = ('sender__username', 'recipients__username', 'unit__name', 'task__name')

    @admin.display(description="Recipients")
    def get_recipients(self, obj):
        return ", ".join([u.username for u in obj.recipients.all()])

    @admin.display(description="Task", ordering="task__name")
    def task_name(self, obj):
        return obj.task.name if obj.task else "--"
