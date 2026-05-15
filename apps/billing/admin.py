from decimal import Decimal, ROUND_HALF_UP

from django.contrib import admin
from django import forms

from .models import CreditLedgerEntry, CreditPack, Purchase


class CreditPackAdminForm(forms.ModelForm):
    price_dollars = forms.DecimalField(
        label="Price",
        min_value=Decimal("0.01"),
        max_digits=8,
        decimal_places=2,
        help_text="Customer-facing price in dollars. Saved internally as cents.",
    )

    class Meta:
        model = CreditPack
        fields = (
            "name",
            "slug",
            "credits_included",
            "price_dollars",
            "currency",
            "stripe_price_id",
            "is_active",
            "sort_order",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["price_dollars"].initial = Decimal(self.instance.price_cents) / 100

    def save(self, commit=True):
        instance = super().save(commit=False)
        price = self.cleaned_data["price_dollars"]
        instance.price_cents = int((price * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(CreditPack)
class CreditPackAdmin(admin.ModelAdmin):
    form = CreditPackAdminForm
    list_display = (
        "sort_order",
        "name",
        "credits_included",
        "price_display",
        "price_per_credit_display",
        "stripe_price_id",
        "is_active",
    )
    list_display_links = ("name",)
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "slug", "stripe_price_id")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Price")
    def price_display(self, obj):
        return f"${obj.price_dollars:.2f}"

    @admin.display(description="Per credit")
    def price_per_credit_display(self, obj):
        if not obj.credits_included:
            return "-"
        return f"${obj.price_cents / obj.credits_included / 100:.2f}"


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("email", "credit_pack", "status", "amount_cents", "created_at")
    list_filter = ("status", "credit_pack")
    search_fields = ("email", "stripe_checkout_session_id", "stripe_payment_intent_id")


@admin.register(CreditLedgerEntry)
class CreditLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("email", "entry_type", "amount", "balance_after", "source", "created_at")
    list_filter = ("entry_type", "source")
    search_fields = ("email", "source_id", "stripe_checkout_session_id")
    readonly_fields = ("created_at",)
