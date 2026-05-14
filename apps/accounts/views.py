import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.billing.models import Purchase
from apps.billing.services import get_credit_balance
from apps.songs.models import SongRequest

from .forms import EmailLoginForm
from .services import consume_email_login_token, get_or_create_email_user, send_email_login_link


@login_required(login_url="accounts:login")
def dashboard(request):
    email = request.user.email
    songs = SongRequest.objects.filter(email=email).order_by("-created_at")[:12]
    purchases = Purchase.objects.filter(email=email).order_by("-created_at")[:8]
    return render(
        request,
        "accounts/dashboard.html",
        {
            "balance": get_credit_balance(email),
            "songs": songs,
            "purchases": purchases,
        },
    )


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "accounts:dashboard"
    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            send_email_login_link(request, form.cleaned_data["email"], redirect_to=next_url)
            request.session["pending_login_email"] = form.cleaned_data["email"]
            return redirect("accounts:email_sent")
    else:
        form = EmailLoginForm()
    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "next": next_url,
            "google_enabled": google_oauth_enabled(),
            "google_login_url": google_login_url(next_url),
        },
    )


def email_sent(request):
    return render(
        request,
        "accounts/email_sent.html",
        {"email": request.session.get("pending_login_email", "")},
    )


def magic_login(request, token):
    login_token = consume_email_login_token(token)
    if not login_token:
        messages.error(request, "That sign-in link is expired or has already been used.")
        return redirect("accounts:login")
    user = get_or_create_email_user(login_token.email)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, f"Signed in as {user.email}.")
    return redirect(login_token.redirect_to or "accounts:dashboard")


def logout_view(request):
    logout(request)
    messages.success(request, "Signed out.")
    return redirect("web:home")


def google_start(request):
    if not google_oauth_enabled():
        messages.info(request, "Google sign-in needs OAuth credentials before it can be enabled.")
        return redirect("accounts:login")
    next_url = request.GET.get("next") or "accounts:dashboard"
    state = secrets.token_urlsafe(24)
    request.session["google_oauth_state"] = state
    request.session["google_oauth_next"] = next_url
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


def google_callback(request):
    expected_state = request.session.pop("google_oauth_state", "")
    next_url = request.session.pop("google_oauth_next", "") or "accounts:dashboard"
    if not expected_state or request.GET.get("state") != expected_state:
        messages.error(request, "Google sign-in could not be verified. Please try again.")
        return redirect("accounts:login")
    if request.GET.get("error"):
        messages.error(request, "Google sign-in was canceled.")
        return redirect("accounts:login")
    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google did not return a sign-in code.")
        return redirect("accounts:login")
    try:
        email = fetch_google_email(code)
    except requests.RequestException:
        messages.error(request, "Google sign-in failed. Please try email sign-in.")
        return redirect("accounts:login")
    if not email:
        messages.error(request, "Google did not return a verified email address.")
        return redirect("accounts:login")
    user = get_or_create_email_user(email)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, f"Signed in as {user.email}.")
    return redirect(next_url)


def google_oauth_enabled():
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def google_login_url(next_url):
    return f"{reverse('accounts:google')}?{urlencode({'next': next_url})}"


def fetch_google_email(code):
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    token_response.raise_for_status()
    access_token = token_response.json().get("access_token")
    if not access_token:
        return ""
    userinfo_response = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    userinfo_response.raise_for_status()
    profile = userinfo_response.json()
    if not profile.get("email_verified", False):
        return ""
    return profile.get("email", "").strip().lower()
