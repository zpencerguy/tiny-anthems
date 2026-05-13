from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.billing.models import Purchase
from apps.billing.services import get_credit_balance
from apps.songs.models import SongRequest

from .forms import EmailLoginForm
from .services import get_or_create_email_user


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
            user = get_or_create_email_user(form.cleaned_data["email"])
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Signed in as {user.email}.")
            return redirect(next_url)
    else:
        form = EmailLoginForm()
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


def logout_view(request):
    logout(request)
    messages.success(request, "Signed out.")
    return redirect("web:home")


def google_placeholder(request):
    messages.info(
        request,
        "Google sign-in needs OAuth credentials before it can be enabled. Use email sign-in for now.",
    )
    return redirect("accounts:login")
