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
                "generated_title": "Maya's Birthday Jam",
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
        self.assertEqual(song.generated_title, "Maya's Birthday Jam")
        self.assertRedirects(
            response,
            reverse("songs:detail", args=[song.pk, song.access_token]),
            fetch_redirect_response=False,
        )

    def test_song_request_normalizes_user_text_before_save(self):
        self.client.post(
            reverse("songs:create"),
            {
                "email": "  Sender@Example.com ",
                "generated_title": "  Maya\x00  Birthday   Anthem  ",
                "occasion": "birthday",
                "recipient_name": "  Maya\x00   June  ",
                "recipient_nickname": "  MJ\t",
                "milestone": "  30th\n birthday ",
                "relationship": "friend",
                "personal_details": (
                    "  Maya\x00 loves   hiking,\n\n\n breakfast tacos, "
                    "and sending\tperfect reaction gifs.  "
                ),
                "things_to_avoid": "  mean jokes\x07\n\n\n spoilers  ",
                "family_friendly": "on",
                "vibe": "funky_groove",
                "tone": "funny",
            },
        )
        song = SongRequest.objects.get(email="sender@example.com")
        self.assertEqual(song.generated_title, "Maya Birthday Anthem")
        self.assertEqual(song.recipient_name, "Maya June")
        self.assertEqual(song.recipient_nickname, "MJ")
        self.assertEqual(song.milestone, "30th birthday")
        self.assertEqual(
            song.personal_details,
            "Maya loves hiking,\n\nbreakfast tacos, and sending perfect reaction gifs.",
        )
        self.assertEqual(song.things_to_avoid, "mean jokes\n\nspoilers")

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

    def test_song_status_endpoint_returns_current_generation_state(self):
        song = SongRequest.objects.create(
            email="status@example.com",
            status=SongRequestStatus.QUEUED,
            occasion="promotion",
            recipient_name="Jess",
            relationship="coworker",
            personal_details="Jess got promoted after rescuing every Friday deadline.",
            vibe="pop_anthem",
            tone="party_energy",
        )
        response = self.client.get(reverse("songs:status", args=[song.pk, song.access_token]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["song_status"], "queued")
        self.assertEqual(payload["song_status_label"], "Queued")

    def test_song_detail_shows_generation_progress_for_queued_song(self):
        song = SongRequest.objects.create(
            email="status@example.com",
            status=SongRequestStatus.QUEUED,
            occasion="promotion",
            recipient_name="Jess",
            relationship="coworker",
            personal_details="Jess got promoted after rescuing every Friday deadline.",
            vibe="pop_anthem",
            tone="party_energy",
        )
        response = self.client.get(reverse("songs:detail", args=[song.pk, song.access_token]))
        self.assertContains(response, "Your tiny anthem is in the mix.")
        self.assertContains(response, reverse("songs:status", args=[song.pk, song.access_token]))

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

    def test_placeholder_stripe_key_uses_dev_checkout(self):
        pack = ensure_beta_credit_packs()[0]
        with self.settings(STRIPE_SECRET_KEY="replace-with-stripe-secret-key"):
            response = self.client.post(
                reverse("billing:checkout"),
                {"pack": pack.slug, "email": "placeholder@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("dev=1", response["Location"])
