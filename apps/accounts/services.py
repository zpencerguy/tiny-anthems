import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from .models import CustomerProfile, EmailLoginToken


def get_or_create_email_user(email):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=email,
        defaults={"email": email},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    elif user.email != email:
        user.email = email
        user.save(update_fields=["email"])

    profile, _ = CustomerProfile.objects.get_or_create(
        email=email,
        defaults={"user": user, "access_token": secrets.token_urlsafe(32)},
    )
    if profile.user_id != user.id:
        profile.user = user
        profile.save(update_fields=["user", "updated_at"])
    return user


def create_email_login_token(email, redirect_to=""):
    raw_token = secrets.token_urlsafe(32)
    login_token = EmailLoginToken.objects.create(
        email=email,
        token_hash=hash_login_token(raw_token),
        redirect_to=redirect_to,
        expires_at=timezone.now() + settings.EMAIL_LOGIN_TOKEN_TTL,
    )
    return login_token, raw_token


def send_email_login_link(request, email, redirect_to=""):
    login_token, raw_token = create_email_login_token(email, redirect_to=redirect_to)
    path = reverse("accounts:magic_login", args=[raw_token])
    url = request.build_absolute_uri(path)
    send_mail(
        "Your Tiny Anthems sign-in link",
        (
            "Use this private link to sign in to Tiny Anthems:\n\n"
            f"{url}\n\n"
            f"This link expires in {int(settings.EMAIL_LOGIN_TOKEN_TTL.total_seconds() / 60)} minutes."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return login_token


def consume_email_login_token(raw_token):
    token_hash = hash_login_token(raw_token)
    try:
        login_token = EmailLoginToken.objects.get(token_hash=token_hash)
    except EmailLoginToken.DoesNotExist:
        return None
    if not login_token.is_usable:
        return None
    login_token.mark_used()
    return login_token


def hash_login_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
