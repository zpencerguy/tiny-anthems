from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.billing.models import Purchase
from apps.billing.services import ensure_beta_credit_packs, grant_credits_for_purchase
from apps.songs.models import SongRequest

from .models import CustomerProfile


class AccountLoginTests(TestCase):
    def test_email_login_creates_user_and_profile(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"email": "Singer@Example.com", "next": reverse("web:home")},
        )
        self.assertRedirects(response, reverse("web:home"))
        user = get_user_model().objects.get(username="singer@example.com")
        self.assertEqual(user.email, "singer@example.com")
        self.assertTrue(CustomerProfile.objects.filter(email="singer@example.com").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_logout_clears_session(self):
        self.client.post(reverse("accounts:login"), {"email": "singer@example.com"})
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("web:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_shows_balance_songs_and_purchases(self):
        self.client.post(reverse("accounts:login"), {"email": "singer@example.com"})
        pack = ensure_beta_credit_packs()[2]
        purchase = Purchase.objects.create(
            email="singer@example.com",
            credit_pack=pack,
            amount_cents=pack.price_cents,
        )
        grant_credits_for_purchase(purchase, source_id="cs_dashboard")
        SongRequest.objects.create(
            email="singer@example.com",
            occasion="birthday",
            recipient_name="Ari",
            relationship="friend",
            personal_details="Ari loves karaoke, spicy noodles, and making every party louder.",
            vibe="pop_anthem",
            tone="party_energy",
        )

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertContains(response, "3 credits")
        self.assertContains(response, "Ari")
        self.assertContains(response, "Recent purchases")

    def test_header_shows_logged_in_credit_balance(self):
        self.client.post(reverse("accounts:login"), {"email": "singer@example.com"})
        pack = ensure_beta_credit_packs()[0]
        purchase = Purchase.objects.create(
            email="singer@example.com",
            credit_pack=pack,
            amount_cents=pack.price_cents,
        )
        grant_credits_for_purchase(purchase, source_id="cs_header")

        response = self.client.get(reverse("web:home"))

        self.assertContains(response, "1 credit")
