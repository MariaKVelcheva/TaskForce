from urllib.parse import urlencode

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def get_next(request):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nxt
    return None


def with_next(url, next_url):
    return f"{url}?{urlencode({'next': next_url})}" if next_url else url


class NextMixin:
    next_fallback = "all-tasks"

    def get_next_context(self):
        next_url = get_next(self.request)
        return {
            "next_url": next_url,
            "back_url": next_url or reverse(self.next_fallback),
        }