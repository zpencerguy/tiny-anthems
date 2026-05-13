from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.billing.services import ensure_beta_credit_packs, get_credit_balance
from apps.generation.services import start_generation

from .forms import SongRequestForm
from .models import ShareLink, SongRequest, SongRequestStatus


def create_song(request):
    if request.method == "POST":
        post_data = request.POST.copy()
        if request.user.is_authenticated:
            post_data["email"] = request.user.email
        form = SongRequestForm(post_data)
        if form.is_valid():
            song_request = form.save(commit=False)
            if request.user.is_authenticated:
                song_request.user = request.user
                song_request.email = request.user.email
            song_request.status = SongRequestStatus.DRAFT
            song_request.save()
            return redirect("songs:detail", pk=song_request.pk, token=song_request.access_token)
    else:
        initial = {"family_friendly": True}
        if request.user.is_authenticated:
            initial["email"] = request.user.email
        form = SongRequestForm(initial=initial)
    return render(request, "songs/create.html", {"form": form})


def _get_owned_song(pk, token):
    return get_object_or_404(SongRequest, pk=pk, access_token=token)


def song_detail(request, pk, token):
    song_request = _get_owned_song(pk, token)
    ensure_beta_credit_packs()
    balance = get_credit_balance(song_request.email)
    return render(
        request,
        "songs/detail.html",
        {"song_request": song_request, "balance": balance},
    )


def song_status(request, pk, token):
    song_request = _get_owned_song(pk, token)
    latest_job = song_request.generation_jobs.order_by("-created_at").first()
    latest_asset = song_request.assets.order_by("-created_at").first()
    asset_url = ""
    if latest_asset:
        asset_url = latest_asset.public_url or f"/media/{latest_asset.storage_key}"
    return JsonResponse(
        {
            "song_status": song_request.status,
            "song_status_label": song_request.get_status_display(),
            "job_status": latest_job.status if latest_job else None,
            "job_status_label": latest_job.get_status_display() if latest_job else None,
            "error_message": latest_job.error_message if latest_job else "",
            "asset_url": asset_url,
        }
    )


@require_POST
def generate_song(request, pk, token):
    song_request = _get_owned_song(pk, token)
    if not request.POST.get("terms"):
        messages.error(
            request,
            "Confirm the song request is original and does not ask for artist imitation before generating.",
        )
        return redirect("songs:detail", pk=song_request.pk, token=song_request.access_token)
    try:
        job = start_generation(song_request)
        if job.status == "completed":
            messages.success(request, "Your tiny anthem is ready.")
        elif job.status == "refunded":
            messages.error(
                request,
                "Generation failed, so we refunded your credit. Check provider settings or try again.",
            )
        else:
            messages.info(request, "Your tiny anthem is queued. This page will update as it mixes.")
    except ValueError:
        song_request.status = SongRequestStatus.AWAITING_PAYMENT
        song_request.save(update_fields=["status", "updated_at"])
        messages.info(request, "Buy credits first. 1 credit = 1 custom song.")
    return redirect("songs:detail", pk=song_request.pk, token=song_request.access_token)


@require_POST
def create_share_link(request, pk, token):
    song_request = _get_owned_song(pk, token)
    link, _ = ShareLink.objects.get_or_create(song_request=song_request, is_active=True)
    return redirect("songs:public_share", token=link.token)


def public_share(request, token):
    share_link = get_object_or_404(ShareLink, token=token, is_active=True)
    if share_link.song_request.status != SongRequestStatus.COMPLETED:
        raise Http404
    ShareLink.objects.filter(pk=share_link.pk).update(view_count=share_link.view_count + 1)
    return render(request, "songs/share.html", {"share_link": share_link})
