from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage

from .models import SongAsset
from .services import get_download_url


def download_asset(request, asset_id, token):
    asset = get_object_or_404(SongAsset, id=asset_id)
    if not _token_can_access_asset(asset, token):
        raise Http404
    if asset.public_url:
        return HttpResponseRedirect(asset.public_url)
    if asset.metadata.get("storage_backend") == "gcs":
        return HttpResponseRedirect(get_download_url(asset))

    if not default_storage.exists(asset.storage_key):
        raise Http404
    return FileResponse(
        default_storage.open(asset.storage_key, "rb"),
        content_type=asset.mime_type,
        as_attachment=False,
        filename=asset.storage_key.rsplit("/", 1)[-1],
    )


def _token_can_access_asset(asset, token):
    if asset.song_request.access_token == token:
        return True
    return asset.song_request.share_links.filter(token=token, is_active=True).exists()
