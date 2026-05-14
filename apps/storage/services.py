from datetime import timedelta
import json
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.urls import reverse
from django.utils import timezone


class StorageConfigurationError(RuntimeError):
    pass


def build_song_storage_key(
    song_request_id,
    generation_job_id,
    asset_kind,
    extension,
    filename_stem=None,
):
    clean_extension = extension.lstrip(".")
    filename = filename_stem or asset_kind
    return f"songs/{song_request_id}/jobs/{generation_job_id}/{filename}.{clean_extension}"


def upload_bytes(storage_key, content, content_type):
    backend = get_storage_backend()
    return backend.upload_bytes(storage_key, content, content_type)


def get_download_url(song_asset, request=None, token=None):
    backend = get_storage_backend()
    return backend.get_download_url(song_asset, request=request, token=token)


def get_storage_backend():
    if settings.STORAGE_BACKEND == "filesystem":
        return FilesystemStorageBackend()
    if settings.STORAGE_BACKEND == "gcs":
        return GCSStorageBackend()
    raise StorageConfigurationError(f"Unsupported STORAGE_BACKEND: {settings.STORAGE_BACKEND}")


class FilesystemStorageBackend:
    name = "filesystem"

    def upload_bytes(self, storage_key, content, content_type):
        saved_key = default_storage.save(storage_key, content)
        return {
            "storage_backend": self.name,
            "storage_key": saved_key,
            "public_url": "",
            "file_size_bytes": default_storage.size(saved_key),
        }

    def get_download_url(self, song_asset, request=None, token=None):
        access_token = token or song_asset.song_request.access_token
        url = reverse("storage:download", args=[song_asset.id, access_token])
        return request.build_absolute_uri(url) if request else url


class GCSStorageBackend:
    name = "gcs"

    def __init__(self):
        if not settings.GCS_BUCKET_NAME:
            raise StorageConfigurationError("GCS_BUCKET_NAME is required when STORAGE_BACKEND=gcs.")
        from google.cloud import storage
        from google.oauth2 import service_account

        credentials = None
        if settings.GCS_SERVICE_ACCOUNT_JSON:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(settings.GCS_SERVICE_ACCOUNT_JSON)
            )
        self.client = storage.Client(project=settings.GCS_PROJECT_ID or None, credentials=credentials)
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)

    def upload_bytes(self, storage_key, content, content_type):
        blob = self.bucket.blob(storage_key)
        blob.upload_from_file(content, content_type=content_type, rewind=True)
        return {
            "storage_backend": self.name,
            "storage_key": storage_key,
            "public_url": "",
            "file_size_bytes": blob.size or _content_size(content),
        }

    def get_download_url(self, song_asset, request=None, token=None):
        access_token = token or song_asset.song_request.access_token
        if request:
            return request.build_absolute_uri(
                reverse("storage:download", args=[song_asset.id, access_token])
            )
        blob = self.bucket.blob(song_asset.storage_key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timezone.now() + timedelta(seconds=settings.GCS_SIGNED_URL_TTL_SECONDS),
            method="GET",
        )


def _content_size(content):
    position = content.tell()
    content.seek(0, 2)
    size = content.tell()
    content.seek(position)
    return size
