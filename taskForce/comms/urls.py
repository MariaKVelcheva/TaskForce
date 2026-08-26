from django.urls import path, include
from taskForce.comms import views

urlpatterns = [
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path("unit-chat/<int:pk>/", views.OpenUnitChatView.as_view(), name="unit-chat"),
    path("task-chat/<int:pk>/", views.OpenTaskChatView.as_view(), name="task-chat"),
    path("conversation/<int:pk>/", views.ConversationView.as_view(), name="conversation"),
]

