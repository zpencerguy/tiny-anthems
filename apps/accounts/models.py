from django.conf import settings
from django.db import models
from django.utils import timezone


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    email = models.EmailField(unique=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    access_token = models.CharField(max_length=64, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email


class EmailLoginToken(models.Model):
    email = models.EmailField(db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    redirect_to = models.CharField(max_length=500, blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_usable(self):
        return self.used_at is None and self.expires_at > timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    def __str__(self):
        return f"Login token for {self.email}"
