from django.contrib import admin
from taskForce.units.models import Unit, Membership


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_user_names')
    search_fields = ('name', 'users__username')

    @admin.display(description='Usernames')
    def get_user_names(self, obj):
        return ', '.join([u.username for u in obj.users.all()])


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'unit')
    search_fields = ('user__username', 'unit__name')
    list_filter = ('role', )