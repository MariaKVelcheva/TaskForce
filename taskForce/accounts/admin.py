from django.contrib import admin
from taskForce.accounts.models import Avatar
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


User = get_user_model()


class AvatarInline(admin.StackedInline):
    model = Avatar
    can_delete = False
    verbose_name_plural = _('Avatars')


admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (AvatarInline, )
