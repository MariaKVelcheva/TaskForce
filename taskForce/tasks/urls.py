from django.urls import path, include

from taskForce.tasks import views

urlpatterns = [
    path("add/", views.CreateTaskView.as_view(), name="add-task"),
    path("all-tasks/", views.CatalogueTaskView.as_view(), name="all-tasks"),

    path("<int:pk>/", include([
        path("details/", views.DetailTaskView.as_view(), name="details-task"),
        path("update/", views.UpdateTaskView.as_view(), name="update-task"),
        path("delete/", views.DeleteTaskView.as_view(), name="delete-task"),
        path("accomplish/", views.accomplish_task, name="accomplish-task"),
        path("unaccomplish/", views.unaccomplish_task, name="unaccomplish-task"),
        path("deactivate/", views.deactivate_task, name="deactivate-task"),
        path("reactivate/", views.reactivate_task, name="reactivate-task"),
    ])),

    path("<int:task_pk>/items/", include([
        path("add/", views.add_item, name="add-item"),
        path("clear-bought/", views.clear_bought, name="clear-bought"),
        path("<int:item_pk>/toggle/", views.toggle_item, name="toggle-item"),
        path("<int:item_pk>/need-now/", views.need_item_now, name="need-item-now"),
        path("<int:item_pk>/stock/", views.adjust_stock, name="adjust-stock"),
        path("<int:item_pk>/amount/", views.set_item_amount, name="set-item-amount"),
        path("<int:item_pk>/delete/", views.delete_item, name="delete-item"),
    ])),
]

