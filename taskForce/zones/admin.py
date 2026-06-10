from django.contrib import admin
from taskForce.zones.models import Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'scene_position', )
    search_fields = ('name', )
