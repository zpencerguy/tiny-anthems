import secrets

from django.conf import settings
from django.db import models

from .sanitization import normalize_single_line


class SongRequestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    AWAITING_PAYMENT = "awaiting_payment", "Awaiting Payment"
    QUEUED = "queued", "Queued"
    GENERATING = "generating", "Generating"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELED = "canceled", "Canceled"


class ModerationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    BLOCKED = "blocked", "Blocked"
    NEEDS_REVIEW = "needs_review", "Needs Review"


class SongRequest(models.Model):
    OCCASION_CHOICES = [
        ("birthday", "Birthday"),
        ("congratulations", "Congratulations"),
        ("graduation", "Graduation"),
        ("promotion", "Promotion"),
        ("roast", "Roast"),
    ]
    VIBE_CHOICES = [
        ("pop_anthem", "Pop Anthem"),
        ("funky_groove", "Funky Groove"),
        ("country_singalong", "Country Singalong"),
        ("acoustic_sweet", "Acoustic Sweet"),
        ("club_banger", "Club Banger"),
    ]
    TONE_CHOICES = [
        ("funny", "Funny"),
        ("sweet", "Sweet"),
        ("light_roast", "Light Roast"),
        ("wholesome", "Wholesome"),
        ("party_energy", "Party Energy"),
    ]
    RELATIONSHIP_CHOICES = [
        ("friend", "Friend"),
        ("partner", "Partner"),
        ("child", "Child"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("coworker", "Coworker"),
        ("boss", "Boss"),
        ("teammate", "Teammate"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    status = models.CharField(
        max_length=30, choices=SongRequestStatus.choices, default=SongRequestStatus.DRAFT
    )
    occasion = models.CharField(max_length=40, choices=OCCASION_CHOICES)
    recipient_name = models.CharField(max_length=80)
    recipient_nickname = models.CharField(max_length=80, blank=True)
    milestone = models.CharField(max_length=80, blank=True)
    relationship = models.CharField(max_length=40, choices=RELATIONSHIP_CHOICES)
    personal_details = models.TextField()
    things_to_avoid = models.TextField(blank=True)
    family_friendly = models.BooleanField(default=True)
    tone = models.CharField(max_length=40, choices=TONE_CHOICES)
    vibe = models.CharField(max_length=40, choices=VIBE_CHOICES)
    requested_duration_seconds = models.PositiveSmallIntegerField(default=15)
    generated_title = models.CharField(max_length=160, blank=True)
    lyrics_preview = models.TextField(blank=True)
    prompt_used = models.TextField(blank=True)
    moderation_status = models.CharField(
        max_length=30, choices=ModerationStatus.choices, default=ModerationStatus.PENDING
    )
    access_token = models.CharField(max_length=64, unique=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        self.generated_title = normalize_single_line(self.generated_title)
        if not self.access_token:
            self.access_token = secrets.token_urlsafe(32)
        if not self.generated_title and self.recipient_name:
            occasion = self.get_occasion_display()
            self.generated_title = f"{self.recipient_name}'s {occasion} Anthem"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.generated_title or f"Song for {self.recipient_name}"


class ShareLink(models.Model):
    song_request = models.ForeignKey(SongRequest, on_delete=models.CASCADE, related_name="share_links")
    token = models.CharField(max_length=64, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.token
