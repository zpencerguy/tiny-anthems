from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import Mock, patch
from datetime import timedelta

from apps.billing.models import Purchase
from apps.billing.services import ensure_beta_credit_packs, grant_credits_for_purchase
from apps.songs.models import ShareLink, SongRequest, SongRequestStatus
from apps.storage.models import SongAsset

from .models import CustomerProfile, EmailLoginToken
from .services import hash_login_token


class AccountLoginTests(TestCase):
    def test_email_login_sends_magic_link_without_creating_session(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "Singer@Example.com", "next": reverse("web:home")},
        )
        self.assertRedirects(response, reverse("accounts:email_sent"))
        self.assertFalse(get_user_model().objects.filter(username="singer@example.com").exists())
        self.assertTrue(EmailLoginToken.objects.filter(email="singer@example.com").exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_magic_link_creates_user_profile_and_signs_in(self):
        token = "raw-login-token"
        EmailLoginToken.objects.create(
            email="singer@example.com",
            token_hash=hash_login_token(token),
            redirect_to=reverse("web:home"),
            expires_at=timezone.now() + timedelta(minutes=20),
        )

        response = self.client.get(reverse("accounts:magic_login", args=[token]))

        self.assertRedirects(response, reverse("web:home"))
        user = get_user_model().objects.get(username="singer@example.com")
        self.assertEqual(user.email, "singer@example.com")
        self.assertTrue(CustomerProfile.objects.filter(email="singer@example.com").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)
        self.assertIsNotNone(EmailLoginToken.objects.get(email="singer@example.com").used_at)

    def test_magic_link_rejects_reuse(self):
        token = "raw-login-token"
        EmailLoginToken.objects.create(
            email="singer@example.com",
            token_hash=hash_login_token(token),
            expires_at=timezone.now() + timedelta(minutes=20),
        )

        self.client.get(reverse("accounts:magic_login", args=[token]))
        response = self.client.get(reverse("accounts:magic_login", args=[token]))

        self.assertRedirects(response, reverse("accounts:login"))

    def test_logout_clears_session(self):
        user = get_user_model().objects.create_user(username="singer@example.com", email="singer@example.com")
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("web:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_shows_balance_songs_and_purchases(self):
        user = get_user_model().objects.create_user(username="singer@example.com", email="singer@example.com")
        self.client.force_login(user)
        pack = ensure_beta_credit_packs()[2]
        purchase = Purchase.objects.create(
            email="singer@example.com",
            credit_pack=pack,
            amount_cents=pack.price_cents,
        )
        grant_credits_for_purchase(purchase, source_id="cs_dashboard")
        song = SongRequest.objects.create(
            email="singer@example.com",
            status=SongRequestStatus.COMPLETED,
            occasion="birthday",
            recipient_name="Ari",
            relationship="friend",
            personal_details="Ari loves karaoke, spicy noodles, and making every party louder.",
            vibe="pop_anthem",
            tone="party_energy",
        )
        SongAsset.objects.create(
            song_request=song,
            asset_type=SongAsset.AssetType.FINAL_MP3,
            storage_key="processed-audio/ari.mp3",
            mime_type="audio/mpeg",
        )
        share_link = ShareLink.objects.create(song_request=song)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertContains(response, "3 credits")
        self.assertContains(response, "Ari")
        self.assertContains(response, "Recent purchases")
        self.assertContains(response, "<audio")
        self.assertContains(response, "Download")
        self.assertContains(response, "Copy Link")
        self.assertContains(response, reverse("songs:public_share", args=[share_link.token]))

    def test_header_shows_logged_in_credit_balance(self):
        user = get_user_model().objects.create_user(username="singer@example.com", email="singer@example.com")
        self.client.force_login(user)
        pack = ensure_beta_credit_packs()[0]
        purchase = Purchase.objects.create(
            email="singer@example.com",
            credit_pack=pack,
            amount_cents=pack.price_cents,
        )
        grant_credits_for_purchase(purchase, source_id="cs_header")

        response = self.client.get(reverse("web:home"))

        self.assertContains(response, "1 credit")

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/accounts/google/callback/",
    )
    def test_google_start_redirects_to_google_with_state(self):
        response = self.client.get(reverse("accounts:google"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", response["Location"])
        self.assertIn("google_oauth_state", self.client.session)

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/accounts/google/callback/",
    )
    def test_google_callback_creates_user_profile_and_signs_in(self):
        session = self.client.session
        session["google_oauth_state"] = "state-token"
        session["google_oauth_next"] = reverse("web:home")
        session.save()
        token_response = Mock()
        token_response.json.return_value = {"access_token": "access-token"}
        token_response.raise_for_status.return_value = None
        userinfo_response = Mock()
        userinfo_response.json.return_value = {
            "email": "GoogleUser@Example.com",
            "email_verified": True,
        }
        userinfo_response.raise_for_status.return_value = None

        with (
            patch("apps.accounts.views.requests.post", return_value=token_response),
            patch("apps.accounts.views.requests.get", return_value=userinfo_response),
        ):
            response = self.client.get(
                reverse("accounts:google_callback"),
                {"state": "state-token", "code": "auth-code"},
            )

        self.assertRedirects(response, reverse("web:home"))
        user = get_user_model().objects.get(username="googleuser@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)
        self.assertTrue(CustomerProfile.objects.filter(email="googleuser@example.com").exists())
