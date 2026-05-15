from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.urls import reverse

from .models import CreditEntryType, CreditLedgerEntry, CreditPack, Purchase, PurchaseStatus


BETA_PACKS = [
    ("1-credit", "1 Credit", 1, 149),
    ("2-credits", "2 Credits", 2, 279),
    ("3-credits", "3 Credits", 3, 399),
    ("4-credits", "4 Credits", 4, 449),
    ("5-credits", "5 Credits", 5, 499),
]


def ensure_beta_credit_packs():
    packs = []
    for sort_order, (slug, name, credits, price_cents) in enumerate(BETA_PACKS, start=1):
        pack, _ = CreditPack.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "credits_included": credits,
                "price_cents": price_cents,
                "sort_order": sort_order,
            },
        )
        packs.append(pack)
    return packs


def get_credit_balance(email):
    total = (
        CreditLedgerEntry.objects.filter(email=email).aggregate(total=Sum("amount"))["total"] or 0
    )
    return total


def create_ledger_entry(
    *,
    email,
    entry_type,
    amount,
    source,
    source_id,
    user=None,
    song_request=None,
    generation_job=None,
    stripe_checkout_session_id="",
    stripe_payment_intent_id="",
    metadata=None,
):
    with transaction.atomic():
        balance = get_credit_balance(email) + amount
        return CreditLedgerEntry.objects.create(
            user=user,
            email=email,
            entry_type=entry_type,
            amount=amount,
            balance_after=balance,
            source=source,
            source_id=source_id,
            song_request=song_request,
            generation_job=generation_job,
            stripe_checkout_session_id=stripe_checkout_session_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            metadata=metadata or {},
        )


def grant_credits_for_purchase(purchase, *, source_id):
    try:
        return create_ledger_entry(
            email=purchase.email,
            user=purchase.user,
            entry_type=CreditEntryType.GRANT,
            amount=purchase.credit_pack.credits_included,
            source="stripe_checkout",
            source_id=source_id,
            stripe_checkout_session_id=purchase.stripe_checkout_session_id or "",
            stripe_payment_intent_id=purchase.stripe_payment_intent_id or "",
            metadata={"purchase_id": purchase.id},
        )
    except IntegrityError:
        return CreditLedgerEntry.objects.get(source="stripe_checkout", source_id=source_id)


def spend_credit(email, song_request, generation_job):
    if get_credit_balance(email) < 1:
        raise ValueError("Not enough credits")
    return create_ledger_entry(
        email=email,
        user=song_request.user,
        entry_type=CreditEntryType.SPEND,
        amount=-1,
        source="generation_job",
        source_id=f"spend:{generation_job.id}",
        song_request=song_request,
        generation_job=generation_job,
    )


def refund_credit(email, song_request, generation_job, reason):
    return create_ledger_entry(
        email=email,
        user=song_request.user,
        entry_type=CreditEntryType.REFUND,
        amount=1,
        source="system_refund",
        source_id=f"refund:{generation_job.id}",
        song_request=song_request,
        generation_job=generation_job,
        metadata={"reason": reason},
    )


def create_pending_purchase(*, email, credit_pack):
    return Purchase.objects.create(
        email=email,
        credit_pack=credit_pack,
        amount_cents=credit_pack.price_cents,
        currency=credit_pack.currency,
    )


def create_checkout_session_url(request, purchase):
    import stripe

    if not _has_real_stripe_key(settings.STRIPE_SECRET_KEY):
        return reverse("billing:checkout_success") + f"?purchase={purchase.id}&dev=1"

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=purchase.email,
        line_items=[{"price": purchase.credit_pack.stripe_price_id, "quantity": 1}],
        success_url=request.build_absolute_uri(reverse("billing:checkout_success"))
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse("billing:checkout_cancel")),
        client_reference_id=str(purchase.id),
        metadata={"purchase_id": str(purchase.id), "email": purchase.email},
    )
    purchase.stripe_checkout_session_id = session.id
    purchase.save(update_fields=["stripe_checkout_session_id", "updated_at"])
    return session.url


def _has_real_stripe_key(secret_key):
    return bool(secret_key) and secret_key.startswith(("sk_test_", "sk_live_"))


def complete_purchase_from_checkout_session(session):
    purchase_id = session.get("metadata", {}).get("purchase_id") or session.get("client_reference_id")
    purchase = Purchase.objects.get(id=purchase_id)
    purchase.status = PurchaseStatus.COMPLETED
    purchase.stripe_checkout_session_id = session["id"]
    purchase.stripe_payment_intent_id = session.get("payment_intent") or ""
    purchase.stripe_customer_id = session.get("customer") or ""
    purchase.save()
    grant_credits_for_purchase(purchase, source_id=session["id"])
    return purchase
