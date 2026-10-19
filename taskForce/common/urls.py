from django.urls import path

from taskForce.common import views

urlpatterns = [
    path("", views.IndexView.as_view(), name='index'),
    path("debrief/", views.DebriefHomeView.as_view(), name='debrief'),
    path("deploy/", views.DeployIndexView.as_view(), name="deploy"),
    path("deploy/<slug:location>/", views.DeployLocationView.as_view(), name="deploy-location"),
]
