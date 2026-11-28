from django.db import transaction
from django.db.models import OuterRef, Exists
from django.utils.translation import gettext_lazy as _

from taskForce.tasks.models import Task, TaskType
from taskForce.tasks.rooms import create_default_rooms
from taskForce.units.models import Membership, Unit

SINGLETON_NAMES = {
    TaskType.GROCERIES: _("Grocery list"),
    TaskType.PANTRY: _("Pantry"),
    TaskType.CHORES: _("House cleaning"),
    TaskType.WORKOUT: _("Training"),
}

GROUP_SINGLETONS = [TaskType.GROCERIES, TaskType.PANTRY, TaskType.CHORES]
PERSONAL_SINGLETONS = GROUP_SINGLETONS + [TaskType.WORKOUT]


def create_unit(*, name, commander, personal=False):
    with transaction.atomic():
        unit = Unit.objects.create(
            name=name,
            created_by=commander,
            personal_for=commander if personal else None,
        )
        Membership.objects.create(
            unit=unit,
            user=commander,
            role=Membership.Role.COMMANDER,
        )
        types = PERSONAL_SINGLETONS if personal else GROUP_SINGLETONS
        tasks = Task.objects.bulk_create([
            Task(unit=unit, type=t, name=SINGLETON_NAMES[t], user=commander)
            for t in types
        ])
        chores = next(task for task in tasks if task.type == TaskType.CHORES)
        create_default_rooms(chores)
    return unit


def create_personal_unit(user):
    return create_unit(
        name=_("%(name)s's base") % {"name": user.username},
        commander=user,
        personal=True,
    )


def active_unit_for(user):
    unit = user.avatar.active_unit
    if unit and Membership.objects.filter(unit=unit, user=user).exists():
        return unit
    return user.personal_unit


def commanded_by(user):
    return Unit.objects.filter(
        memberships__user=user,
        memberships__role=Membership.Role.COMMANDER,
    )


def blocking_commands(user):
    others = Membership.objects.filter(unit=OuterRef("pk")).exclude(user=user)
    return commanded_by(user).filter(
        personal_for__isnull=True,
    ).filter(Exists(others))

