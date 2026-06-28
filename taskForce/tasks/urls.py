from django.urls import path, include

from taskForce.tasks import views

urlpatterns = [
    path("add/", views.CreateTaskView.as_view(), name="add-task"),
    path("<int:pk>/", include([
        path("update/", views.UpdateTaskView.as_view(), name="update-task"),
        path("delete/", views.DeleteTaskView.as_view(), name="delete-task"),
        path("details/", views.DetailTaskView.as_view(), name="details-task"),
        path("complete/", views.complete_task, name="complete-task"),
    ])),
    path("all-tasks/", views.CatalogueTaskView.as_view(), name="all-tasks"),
]