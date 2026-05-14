from django.urls import path

from . import views

app_name = "storage"

urlpatterns = [
    path("assets/<int:asset_id>/<str:token>/download/", views.download_asset, name="download"),
]
