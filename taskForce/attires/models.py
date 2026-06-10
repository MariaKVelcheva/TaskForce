from django.db import models
from django.utils.translation import gettext_lazy as _


class Color(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Name'),
    )

    hex_code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_('Hex Code'),
    )

    def __str__(self):
        return self.name


class ClothingPiece(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Name'),
    )


class Attire(models.Model):
    colors = models.ManyToManyField(
        to=Color,
        verbose_name=_('Colors'),
        related_name='attires',
    )

    clothing_pieces = models.ManyToManyField(
        to=ClothingPiece,
        verbose_name=_('Clothing pieces'),
        related_name='attires',
    )

    avatar = models.ForeignKey(
        to="accounts.Avatar",
        on_delete=models.CASCADE,
        verbose_name=_('Avatar'),
        related_name='attires',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Attire')
        verbose_name_plural = _('Attires')

