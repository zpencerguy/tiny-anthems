from django.conf import settings
from django.db import models


class CreditEntryType(models.TextChoices):
    GRANT = "grant", "Grant"
    SPEND = "spend", "Spend"
    REFUND = "refund", "Refund"
    ADJUSTMENT = "adjustment", "Adjustment"


class PurchaseStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"
    REFUNDED = "refunded", "Refunded"


class CreditPack(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    credits_included = models.PositiveSmallIntegerField()
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    stripe_price_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "credits_included")

    def __str__(self):
        return f"{self.credits_included} credits"

    @property
    def price_dollars(self):
        return self.price_cents / 100


class Purchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    credit_pack = models.ForeignKey(CreditPack, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20, choices=PurchaseStatus.choices, default=PurchaseStatus.PENDING
    )
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    stripe_checkout_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} - {self.credit_pack}"


class CreditLedgerEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    entry_type = models.CharField(max_length=20, choices=CreditEntryType.choices)
    amount = models.IntegerField()
    balance_after = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=60)
    source_id = models.CharField(max_length=255)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    song_request = models.ForeignKey(
        "songs.SongRequest", on_delete=models.SET_NULL, null=True, blank=True
    )
    generation_job = models.ForeignKey(
        "generation.GenerationJob", on_delete=models.SET_NULL, null=True, blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "source_id"], name="unique_credit_source")
        ]
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.email} {self.entry_type} {self.amount}"
