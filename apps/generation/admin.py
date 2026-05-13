from django.contrib import admin

from .models import GenerationJob


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ("song_request", "provider", "status", "attempt_number", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("song_request__recipient_name", "provider_request_id", "error_message")
    readonly_fields = ("created_at", "updated_at", "started_at", "completed_at")
