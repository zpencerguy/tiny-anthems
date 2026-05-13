from django.test import TestCase
from django.urls import reverse

from apps.billing.services import ensure_beta_credit_packs
from apps.billing.services import get_credit_balance
from apps.songs.models import ShareLink, SongRequest, SongRequestStatus
from apps.storage.models import SongAsset


class HomePageTests(TestCase):
    def test_homepage_shows_examples_and_credit_pricing(self):
        response = self.client.get(reverse("web:home"))
        self.assertContains(response, "1 credit = 1 custom song")
        self.assertContains(response, "Funky Birthday Song for Mike")
        self.assertContains(response, "$1.00")
        self.assertContains(response, "$4.00")

    def test_valid_song_request_redirects_to_review(self):
        response = self.client.post(
            reverse("songs:create"),
            {
                "email": "sender@example.com",
                "occasion": "birthday",
                "recipient_name": "Maya",
                "recipient_nickname": "May",
                "milestone": "30th",
                "relationship": "friend",
                "personal_details": "Maya loves hiking, breakfast tacos, and sending perfect reaction gifs.",
                "things_to_avoid": "",
                "family_friendly": "on",
                "vibe": "funky_groove",
                "tone": "funny",
            },
        )
        song = SongRequest.objects.get(email="sender@example.com")
        self.assertRedirects(
            response,
            reverse("songs:detail", args=[song.pk, song.access_token]),
            fetch_redirect_response=False,
        )

    def test_signed_in_song_request_uses_account_email(self):
        self.client.post(reverse("accounts:login"), {"email": "account@example.com"})
        response = self.client.post(
            reverse("songs:create"),
            {
                "email": "different@example.com",
                "occasion": "birthday",
                "recipient_name": "Maya",
                "recipient_nickname": "",
                "milestone": "",
                "relationship": "friend",
                "personal_details": "Maya loves hiking, breakfast tacos, and sending perfect reaction gifs.",
                "things_to_avoid": "",
                "family_friendly": "on",
                "vibe": "funky_groove",
                "tone": "funny",
            },
        )
        song = SongRequest.objects.get(recipient_name="Maya")
        self.assertEqual(song.email, "account@example.com")
        self.assertEqual(song.user.email, "account@example.com")
        self.assertEqual(response.status_code, 302)

    def test_share_page_hides_private_data(self):
        song = SongRequest.objects.create(
            email="private@example.com",
            status=SongRequestStatus.COMPLETED,
            occasion="promotion",
            recipient_name="Jess",
            relationship="coworker",
            personal_details="Jess got promoted after rescuing every Friday deadline.",
            vibe="pop_anthem",
            tone="party_energy",
            prompt_used="internal prompt should not leak",
        )
        SongAsset.objects.create(
            song_request=song,
            asset_type="final_mp3",
            storage_key="processed-audio/test.mp3",
            mime_type="audio/mpeg",
        )
        link = ShareLink.objects.create(song_request=song)
        response = self.client.get(reverse("songs:public_share", args=[link.token]))
        self.assertContains(response, "Jess")
        self.assertNotContains(response, "private@example.com")
        self.assertNotContains(response, "internal prompt should not leak")

    def test_checkout_requires_email(self):
        pack = ensure_beta_credit_packs()[0]
        response = self.client.post(reverse("billing:checkout"), {"pack": pack.slug})
        self.assertEqual(response.status_code, 400)

    def test_dev_checkout_success_grants_credits(self):
        pack = ensure_beta_credit_packs()[1]
        response = self.client.post(
            reverse("billing:checkout"),
            {"pack": pack.slug, "email": "dev@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        success_response = self.client.get(response["Location"])
        self.assertEqual(success_response.status_code, 200)
        self.assertEqual(get_credit_balance("dev@example.com"), 2)
