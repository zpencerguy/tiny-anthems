from django.conf import settings
from django.db import models


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
