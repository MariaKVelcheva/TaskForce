from django.contrib import admin
from taskForce.attires.models import Attire, Color, ClothingPiece


@admin.register(Attire)
class AttireAdmin(admin.ModelAdmin):
    pass


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    pass


@admin.register(ClothingPiece)
class ClothingPieceAdmin(admin.ModelAdmin):
    pass
