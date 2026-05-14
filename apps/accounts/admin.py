from django.contrib import admin

from .models import CustomerProfile, EmailLoginToken


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("email", "stripe_customer_id", "created_at")
    search_fields = ("email", "stripe_customer_id")


@admin.register(EmailLoginToken)
class EmailLoginTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "expires_at", "used_at", "created_at")
    search_fields = ("email",)
    readonly_fields = ("email", "token_hash", "redirect_to", "expires_at", "used_at", "created_at")
