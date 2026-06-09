from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Zone(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
    )

    slug = models.SlugField(
        max_length=100,
        verbose_name=_('Slug'),
        editable=False,
        unique=True,
        null=True,
        blank=True,
    )

    scene_position = models.JSONField(
        default=dict,
        verbose_name=_('Scene position'),
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
