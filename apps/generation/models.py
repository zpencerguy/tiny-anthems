from django.conf import settings
from django.db import models


class GenerationJobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class GenerationJob(models.Model):
    song_request = models.ForeignKey(
        "songs.SongRequest", on_delete=models.CASCADE, related_name="generation_jobs"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.CharField(max_length=40, default="elevenlabs")
    status = models.CharField(
        max_length=30, choices=GenerationJobStatus.choices, default=GenerationJobStatus.QUEUED
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    provider_request_id = models.CharField(max_length=255, blank=True)
    provider_response_metadata = models.JSONField(default=dict, blank=True)
    provider_cost_units = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)
    raw_audio_file = models.FileField(upload_to="raw-audio/", blank=True)
    processed_audio_file = models.FileField(upload_to="processed-audio/", blank=True)
    duration_seconds = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.song_request} attempt {self.attempt_number}"
