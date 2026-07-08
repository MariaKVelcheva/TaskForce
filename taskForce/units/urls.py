from django.urls import path, include
from taskForce.units import views

urlpatterns = [
    path("create/", views.CreateUnitView.as_view(), name="create-unit"),
    path("all-units/", views.CatalogueUnitView.as_view(), name="all-units"),
    path("join/<uuid:invite_code>/", views.join_unit, name="join-unit"),
    path("<int:pk>/", include([
        path("update/", views.UpdateUnitView.as_view(), name="update-unit"),
        path("delete/", views.DeleteUnitView.as_view(), name="delete-unit"),
        path("details/", views.DetailUnitView.as_view(), name="details-unit"),
    ]))
]