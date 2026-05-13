from django.contrib import admin

from .models import CreditLedgerEntry, CreditPack, Purchase


@admin.register(CreditPack)
class CreditPackAdmin(admin.ModelAdmin):
    list_display = ("name", "credits_included", "price_cents", "stripe_price_id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "stripe_price_id")


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
