from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def late_by(due):
    return timesince(due, timezone.now(), depth=1)

