from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from taskForce.tasks.models import Room, Task, TaskType


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ("name",)
        labels = {"name": _("Room name")}

    def clean_name(self):
        name = self.cleaned_data["name"]
        taken = (
            Room.objects
            .filter(task_id=self.instance.task_id, name__iexact=name)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if taken:
            raise forms.ValidationError(
                _("There is already a room called %(name)s."),
                params={"name": name},
                code="duplicate",
            )
        return name


def _chores_for(user, task_pk):
   return get_object_or_404(Task.objects.visible_to(user), pk=task_pk, type=TaskType.CHORES)


def _back(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("deploy-location", "barracks")


def _report_errors(request, form):
    for errors in form.errors.values():
        messages.error(request, errors[0])


@login_required
@require_POST
def add_room(request, task_pk):
    chores = _chores_for(request.user, task_pk)
    form = RoomForm(request.POST, instance=Room(task=chores))
    if form.is_valid():
        form.save()
    else:
        _report_errors(request, form)
    return _back(request)


@login_required
@require_POST
def rename_room(request, task_pk, room_pk):
    chores = _chores_for(request.user, task_pk)
    room = get_object_or_404(Room, pk=room_pk, task=chores)
    form = RoomForm(request.POST, instance=room)
    if form.is_valid():
        form.save()
    else:
        _report_errors(request, form)
    return _back(request)


@login_required
@require_POST
def delete_room(request, task_pk, room_pk):
    chores = _chores_for(request.user, task_pk)
    room = get_object_or_404(Room, pk=room_pk, task=chores)
    name = room.name
    room.delete()
    messages.success(request, _("%(name)s removed. Its duties moved to General.") % {"name": name})
    return _back(request)

