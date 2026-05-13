from django.db import models


class SongAsset(models.Model):
    ASSET_TYPES = [
        ("raw_audio", "Raw Audio"),
        ("final_mp3", "Final MP3"),
        ("waveform_json", "Waveform JSON"),
        ("cover_image", "Cover Image"),
        ("video_card", "Video Card"),
    ]
    song_request = models.ForeignKey(
        "songs.SongRequest", on_delete=models.CASCADE, related_name="assets"
    )
    generation_job = models.ForeignKey(
        "generation.GenerationJob", on_delete=models.SET_NULL, null=True, blank=True
    )
    asset_type = models.CharField(max_length=40, choices=ASSET_TYPES)
    storage_key = models.CharField(max_length=500)
    public_url = models.URLField(blank=True)
    mime_type = models.CharField(max_length=100)
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.song_request} {self.asset_type}"
