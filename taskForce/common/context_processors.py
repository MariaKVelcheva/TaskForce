from django.db.models import Q
from taskForce.comms.models import Message, MessageRead


def unread_count(request):
    if not request.user.is_authenticated:
        return {'unread_count': 0}

    read_ids = set(
        MessageRead.objects.filter(
            user=request.user
        ).values_list('message_id', flat=True)
    )

    count = Message.objects.filter(
        Q(recipients=request.user)
    ).exclude(
        pk__in=read_ids
    ).distinct().count()

    return {'unread_count': count}