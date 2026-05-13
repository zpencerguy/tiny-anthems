from django.contrib import admin

from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("email", "stripe_customer_id", "created_at")
    search_fields = ("email", "stripe_customer_id")
