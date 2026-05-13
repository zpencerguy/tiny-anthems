from django.contrib import admin

from .models import SongAsset


@admin.register(SongAsset)
class SongAssetAdmin(admin.ModelAdmin):
    list_display = ("song_request", "asset_type", "mime_type", "duration_seconds", "created_at")
    list_filter = ("asset_type", "mime_type")
    search_fields = ("song_request__recipient_name", "storage_key")
