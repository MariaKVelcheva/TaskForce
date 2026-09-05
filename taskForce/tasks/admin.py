from django.contrib import admin
from taskForce.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'type', 'unit', 'is_done', 'created_at', 'assigned_to')
    list_filter = ('unit', 'user__username', 'is_done', 'type', )
    search_fields = ('name', 'user__username', 'unit__name', 'assigned_to__username')
    date_hierarchy = 'created_at'
