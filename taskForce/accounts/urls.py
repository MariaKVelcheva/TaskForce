from django.urls import path

from taskForce.accounts import views

urlpatterns = [
    path('register/', views.RegisterUserView.as_view(), name='register'),
    path('login/', views.LoginUserView.as_view(), name='login'),
    path('logout/', views.LogoutUserView.as_view(), name='logout'),
    path('update/', views.UpdateAvatarView.as_view(), name='update-profile'),
    path('delete/', views.DeleteUserView.as_view(), name='delete-user'),
    path('details/', views.ProfileDetailsView.as_view(), name='details-profile'),
]