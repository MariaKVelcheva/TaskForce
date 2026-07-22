from django.urls import path, include
from taskForce.zones import views

urlpatterns = [
    #path("zone-map/", views.zone_scene_data, name="zone-map"),
    path("all-zones/", views.AllZonesView.as_view(), name="all-zones"),
    path("<slug:slug>/details/", views.ZoneDetailView.as_view(), name="details-zone"),
]