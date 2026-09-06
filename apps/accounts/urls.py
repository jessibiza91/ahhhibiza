from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.RateLimitedLoginView.as_view(), name='login'),
    # LogoutView in recent Django versions might require GET/POST handling adjustments, but standard is GET for simple logout or POST.
    # Configuring 'next_page' to home.
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    # Recuperacion de contrasena (flujo completo de Django con SMTP)
    path('reset/password/', views.RateLimitedPasswordResetView.as_view(), name='password_reset'),
    path('reset/password/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    # Cambio de contrasena (usuario ya logueado)
    path('cambiar-contrasena/', views.RateLimitedPasswordChangeView.as_view(), name='password_change'),
    path('cambiar-contrasena/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html',
    ), name='password_change_done'),
    path('register/', views.register_selector, name='register_selector'),
    path('register/client/', views.client_register, name='client_register'),
    path('register/professional/', views.professional_register, name='professional_register'),
    path('dispatch/', views.user_dispatch, name='user_dispatch'),
    path('cliente/', views.client_dashboard, name='client_dashboard'),
    path('favoritos/<int:ad_id>/toggle/', views.toggle_favorite_ad, name='toggle_favorite_ad'),
    path('control/', views.control_panel, name='control_panel'),
    path('control/profesionales/', views.control_professionals, name='control_professionals'),
    path('control/clientes/', views.control_clients, name='control_clients'),
    path('control/materiales/', views.control_media, name='control_media'),
    path('control/movimientos/', views.control_transactions, name='control_transactions'),
    path('control/configuracion/', views.control_site_settings, name='control_site_settings'),
    path('control/profesionales/papelera/', views.control_bulk_trash_users, name='control_bulk_trash_users'),
    path('control/usuario/<int:user_id>/', views.control_user_detail, name='control_user_detail'),
    path('control/papelera/', views.control_trash, name='control_trash'),
    # STRICT NAMING CONVENTION
    path('dashboard/', views.professional_dashboard, name='professional_dashboard'),
    path('dashboard/tangas/', views.professional_wallet, name='professional_wallet'),
    path('dashboard/clientes-favoritos/', views.professional_favorite_clients, name='professional_favorite_clients'),
    path('perfil/editar/', views.profile_edit, name='profile_edit'),
    path('perfil/media/delete/<int:media_id>/', views.delete_profile_media, name='delete_profile_media'),
]
