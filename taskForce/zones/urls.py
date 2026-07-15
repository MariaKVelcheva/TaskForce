from django.urls import path, include
from taskForce.zones import views

urlpatterns = [
    path("all-zones/", views.zone_scene_data, name="zone-scene"),
    path("<slug:slug>/details/", views.ZoneDetailView.as_view(), name="details-zone"),
]