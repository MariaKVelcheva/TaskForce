from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from taskForce.accounts import views

urlpatterns = [
    path('register/', views.RegisterUserView.as_view(), name='register'),
    path('login/', views.LoginUserView.as_view(), name='login'),
    path('logout/', views.LogoutUserView.as_view(), name='logout'),
    path('update/', views.UpdateAvatarView.as_view(), name='update-profile'),
    path('delete/', views.DeleteUserView.as_view(), name='delete-user'),
    path('details/', views.ProfileDetailsView.as_view(), name='details-profile'),

    path('password/', views.ChangePasswordView.as_view(), name='password-change'),
    path('password/reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/emails/password_reset_email.txt',
        subject_template_name='accounts/emails/password_reset_subject.txt',
        success_url=reverse_lazy('password-reset-done'),
    ), name='password-reset'),
    path('password/reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password-reset-done'),
    path('password/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('password-reset-complete'),
    ), name='password-reset-confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password-reset-complete'),
]

