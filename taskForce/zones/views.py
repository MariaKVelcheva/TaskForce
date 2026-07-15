from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView

from taskForce.tasks.models import Task
from taskForce.units.models import Membership, Unit
from taskForce.zones.models import Zone


@login_required
def zone_scene_data(request):
    user = request.user
    unit_ids = Unit.objects.filter(memberships__user=user).values_list('id', flat=True)
    query = Q(tasks__is_done=False) & (Q(tasks__user=user) | Q(tasks__unit__in=unit_ids))
    zones = Zone.objects.annotate(open_tasks=Count("tasks", filter=query, distinct=True))

    return JsonResponse({
        "zones": [
            {
                "slug": zone.slug,
                "name": zone.name,
                "scene_position": zone.scene_position,
                "open_tasks": zone.open_tasks,
                "details_url": reverse("details-zone", kwargs={"slug": zone.slug}),
            }
            for zone in zones
        ]
    })


class ZoneDetailView(DetailView):
    pass