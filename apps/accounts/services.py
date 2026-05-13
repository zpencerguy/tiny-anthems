import secrets

from django.contrib.auth import get_user_model

from .models import CustomerProfile


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
