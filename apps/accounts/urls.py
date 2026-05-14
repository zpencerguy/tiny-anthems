from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("login/sent/", views.email_sent, name="email_sent"),
    path("login/<str:token>/", views.magic_login, name="magic_login"),
    path("logout/", views.logout_view, name="logout"),
    path("google/", views.google_start, name="google"),
    path("google/callback/", views.google_callback, name="google_callback"),
]
