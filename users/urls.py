from django.urls import path
from users.views import UserListView, UserCreateView, UserProfileView, UserUpdateView, UserDeleteView, UserLoginView
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/user_form/', UserCreateView.as_view(), name='create_user'),
    path('users/update/<int:pk>/', UserUpdateView.as_view(), name='update_user'),
    path('users/delete/<int:pk>', UserDeleteView.as_view(), name='delete_user'),
    path('users/login/', UserLoginView.as_view(), name='login'),
    path('users/logout/', LogoutView.as_view(next_page='login'), name='logout'),    
    path('recuperar-cuenta/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='users/recovery/password_reset_done.html'), name='password_reset_done'),
    path('recuperar-cuenta/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='users/recovery/password_reset_confirm.html'), name='password_reset_confirm'),
    path('recuperar-cuenta/completo/', auth_views.PasswordResetCompleteView.as_view(template_name='users/recovery/password_reset_complete.html'), name='password_reset_complete'),
    path('recuperar-cuenta/', auth_views.PasswordResetView.as_view(
        template_name='users/recovery/password_reset.html',
        html_email_template_name='users/recovery/password_reset_email.html', # Parámetro clave para que Django envíe el HTML renderizado
        email_template_name='users/recovery/password_reset_email.txt',
        subject_template_name='users/recovery/password_reset_subject.txt'
    ), name='password_reset'),
    
    # URL dedicada para el perfil (sin <int:pk>)
    path('mi-perfil/', UserProfileView.as_view(), name='my_profile'),
]