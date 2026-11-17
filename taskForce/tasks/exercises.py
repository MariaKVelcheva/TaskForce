from django.db.models import F, Q

from taskForce.tasks.models import Exercise


def _visible_to(user):
    return Exercise.objects.filter(Q(owner__isnull=True) | Q(owner=user))


def find_or_create_exercise(user, name):
    name = " ".join(name.split())
    match = (
        _visible_to(user)
        .filter(name__iexact=name)
        .order_by(F("owner").asc(nulls_first=True))
        .first()
    )
    if match is not None:
        return match
    return Exercise.objects.create(name=name, owner=user)


def library_names(user):
    return list(_visible_to(user).order_by("name").values_list("name", flat=True))