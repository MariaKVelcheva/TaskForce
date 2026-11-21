from django.urls import path

from taskForce.budget import views

urlpatterns = [
    path("unit/<int:unit_pk>/log/", views.log_spending_view, name="unit-log-spending"),
    path("mission/<int:task_pk>/log/", views.log_spending_view, name="mission-log-spending"),
    path("unit/<int:unit_pk>/budget/", views.set_budget_view, name="unit-set-budget"),
    path("mission/<int:task_pk>/budget/", views.set_budget_view, name="mission-set-budget"),
    path("spending/<int:pk>/delete/", views.delete_spending_view, name="delete-spending"),
]

