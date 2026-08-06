from django.urls import path

from taskForce.common import views

urlpatterns = [
    path("", views.IndexView.as_view(), name='index'),
    path("home/", views.DebriefHomeView.as_view(), name='home'),
]
