from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("checkout/review/", views.checkout_review, name="checkout_review"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/success/", views.checkout_success, name="checkout_success"),
    path("checkout/cancel/", views.checkout_cancel, name="checkout_cancel"),
    path("api/stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
