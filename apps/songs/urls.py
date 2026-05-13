from django.urls import path

from . import views

app_name = "songs"

urlpatterns = [
    path("make/", views.create_song, name="create"),
    path("songs/<int:pk>/<str:token>/", views.song_detail, name="detail"),
    path("songs/<int:pk>/<str:token>/generate/", views.generate_song, name="generate"),
    path("songs/<int:pk>/<str:token>/share/", views.create_share_link, name="share"),
    path("s/<str:token>/", views.public_share, name="public_share"),
]
