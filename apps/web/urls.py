from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("healthz/", views.health, name="health"),
    path("", views.home, name="home"),
]
