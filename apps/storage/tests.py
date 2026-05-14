from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.songs.models import SongRequest

from .models import SongAsset
from .services import build_song_storage_key, get_download_url, upload_bytes


class StorageServiceTests(TestCase):
    def test_build_song_storage_key(self):
        self.assertEqual(
            build_song_storage_key(12, 34, "final", "mp3"),
            "songs/12/jobs/34/final.mp3",
        )

    def test_build_song_storage_key_uses_filename_stem_inside_unique_prefix(self):
        self.assertEqual(
            build_song_storage_key(
                12,
                34,
                "final",
                ".mp3",
                filename_stem="mayas-birthday-anthem",
            ),
            "songs/12/jobs/34/mayas-birthday-anthem.mp3",
        )

    @override_settings(STORAGE_BACKEND="filesystem")
    def test_filesystem_upload_and_download_route(self):
        upload = upload_bytes(
            "songs/1/jobs/2/final.txt",
            ContentFile(b"hello"),
            "text/plain",
        )
        song = SongRequest.objects.create(
            email="storage@example.com",
            occasion="birthday",
            recipient_name="Maya",
            relationship="friend",
            personal_details="Maya loves storage tests and tiny songs.",
            vibe="pop_anthem",
            tone="funny",
        )
        asset = SongAsset.objects.create(
            song_request=song,
            asset_type="final_mp3",
            storage_key=upload["storage_key"],
            mime_type="text/plain",
            metadata={"storage_backend": "filesystem"},
        )

        self.assertEqual(upload["storage_backend"], "filesystem")
        self.assertGreater(upload["file_size_bytes"], 0)
        download_path = reverse("storage:download", args=[asset.id, song.access_token])
        self.assertEqual(get_download_url(asset), download_path)
        response = self.client.get(download_path)
        self.assertEqual(response.status_code, 200)

    @override_settings(STORAGE_BACKEND="filesystem")
    def test_download_requires_song_or_share_token(self):
        upload = upload_bytes(
            "songs/1/jobs/2/private.txt",
            ContentFile(b"secret"),
            "text/plain",
        )
        song = SongRequest.objects.create(
            email="storage@example.com",
            occasion="birthday",
            recipient_name="Maya",
            relationship="friend",
            personal_details="Maya loves storage tests and tiny songs.",
            vibe="pop_anthem",
            tone="funny",
        )
        asset = SongAsset.objects.create(
            song_request=song,
            asset_type="final_mp3",
            storage_key=upload["storage_key"],
            mime_type="text/plain",
            metadata={"storage_backend": "filesystem"},
        )

        response = self.client.get(reverse("storage:download", args=[asset.id, "wrong-token"]))

        self.assertEqual(response.status_code, 404)
