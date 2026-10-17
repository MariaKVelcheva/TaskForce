import zoneinfo
from django.utils import timezone


class UserTimeZoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = None
        if request.user.is_authenticated:
            avatar = getattr(request.user, "avatar", None)
            tzname = getattr(avatar, "time_zone", None)
        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()
        return self.get_response(request)