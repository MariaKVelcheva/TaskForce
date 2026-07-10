from django.urls import path, include
from taskForce.comms import views

urlpatterns = [
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("unit/<int:pk>/", views.UnitChatView.as_view(), name="unit-chat"),
    path("task/<int:pk>/", views.ChatThreadView.as_view(), name="chat-thread"),
    path("create/", views.CreateMessageView.as_view(), name="create-message"),
    path("<int:pk>/", include([
        path("delete/", views.DeleteMessageView.as_view(), name="delete-message"),
        path("details/", views.DetailsMessageView.as_view(), name="details-message"),
    ]))
]