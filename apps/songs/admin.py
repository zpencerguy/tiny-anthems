from django.contrib import admin

from .models import ShareLink, SongRequest


@admin.register(SongRequest)
class SongRequestAdmin(admin.ModelAdmin):
    list_display = ("generated_title", "email", "occasion", "status", "moderation_status", "created_at")
    list_filter = ("status", "occasion", "vibe", "tone", "moderation_status")
    search_fields = ("email", "recipient_name", "personal_details", "generated_title")
    readonly_fields = ("access_token", "created_at", "updated_at")


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ("token", "song_request", "is_active", "view_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("token", "song_request__recipient_name")
    actions = ["deactivate_links"]

    @admin.action(description="Deactivate selected share links")
    def deactivate_links(self, request, queryset):
        queryset.update(is_active=False)
