import datetime

from django.db.models import OuterRef, Subquery, Value, F
from django.db.models.functions import Coalesce
from taskForce.comms.models import Message, ConversationRead


def unread_count(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user

    my_read = ConversationRead.objects.filter(
        conversation=OuterRef("conversation"),
        user=user,
    ).values("last_read_at")[:1]

    count = (
        Message.objects.filter(conversation__unit__memberships__user=user)
        .exclude(sender=user)
        .annotate(
            last_read_at=Coalesce(
                Subquery(my_read),
                Value(datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)),
            )
        )
        .filter(created_at__gt=F("last_read_at"))
        .distinct()
        .count()
    )

    return {"unread_count": count}