from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from .models import CreditPack, Purchase, PurchaseStatus
from .services import (
    complete_purchase_from_checkout_session,
    create_checkout_session_url,
    create_pending_purchase,
    ensure_beta_credit_packs,
    grant_credits_for_purchase,
)


@require_http_methods(["GET", "POST"])
def checkout_review(request):
    ensure_beta_credit_packs()
    if request.method == "POST":
        email = (
            request.user.email
            if request.user.is_authenticated
            else request.POST.get("email", "").strip().lower()
        )
        pack = get_object_or_404(CreditPack, slug=request.POST.get("pack"), is_active=True)
        if not email:
            return HttpResponseBadRequest("Email is required.")
        request.session["pending_checkout"] = {"email": email, "pack": pack.slug}
        return redirect("billing:checkout_review")

    pending_checkout = request.session.get("pending_checkout") or {}
    pack_slug = pending_checkout.get("pack")
    email = (
        request.user.email
        if request.user.is_authenticated
        else pending_checkout.get("email", "")
    )
    if not pack_slug or not email:
        return redirect("web:home")
    pack = get_object_or_404(CreditPack, slug=pack_slug, is_active=True)
    return render(request, "billing/checkout_review.html", {"email": email, "pack": pack})


@require_POST
def checkout(request):
    ensure_beta_credit_packs()
    pending_checkout = request.session.get("pending_checkout") or {}
    email = (
        request.user.email
        if request.user.is_authenticated
        else request.POST.get("email", "").strip().lower() or pending_checkout.get("email", "")
    )
    pack_slug = request.POST.get("pack") or pending_checkout.get("pack")
    pack = get_object_or_404(CreditPack, slug=pack_slug, is_active=True)
    if not email:
        return HttpResponseBadRequest("Email is required.")
    if pending_checkout.get("pack") == pack.slug and pending_checkout.get("email") == email:
        request.session.pop("pending_checkout", None)
        request.session.modified = True
    purchase = create_pending_purchase(email=email, credit_pack=pack)
    url = create_checkout_session_url(request, purchase)
    return redirect(url)


def checkout_success(request):
    purchase = None
    if request.GET.get("dev") == "1" and request.GET.get("purchase"):
        purchase = get_object_or_404(Purchase, pk=request.GET["purchase"])
        purchase.status = PurchaseStatus.COMPLETED
        purchase.stripe_checkout_session_id = (
            purchase.stripe_checkout_session_id or f"dev-{purchase.id}"
        )
        purchase.save(update_fields=["status", "stripe_checkout_session_id", "updated_at"])
        grant_credits_for_purchase(purchase, source_id=purchase.stripe_checkout_session_id)
    elif request.GET.get("session_id"):
        purchase = (
            Purchase.objects.filter(stripe_checkout_session_id=request.GET["session_id"])
            .select_related("credit_pack")
            .first()
        )
    return render(request, "billing/checkout_success.html", {"purchase": purchase})


def checkout_cancel(request):
    return render(request, "billing/checkout_cancel.html")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    import stripe

    payload = request.body
    signature = request.headers.get("stripe-signature")
    try:
        if settings.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        else:
            event = stripe.Event.construct_from(request.POST, stripe.api_key)
    except Exception:
        return HttpResponseBadRequest("Invalid webhook")

    if event["type"] == "checkout.session.completed":
        complete_purchase_from_checkout_session(event["data"]["object"])
    return HttpResponse("ok")
