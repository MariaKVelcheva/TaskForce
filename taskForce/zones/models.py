from django.db import models
from django.utils.translation import gettext_lazy as _


class Zone(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
    )
