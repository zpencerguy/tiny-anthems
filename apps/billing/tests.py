from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.generation.models import GenerationJobStatus
from apps.generation.services import start_generation
from apps.songs.models import SongRequest, SongRequestStatus

from .models import CreditEntryType, CreditLedgerEntry, Purchase
from .services import ensure_beta_credit_packs, get_credit_balance, grant_credits_for_purchase


class CreditLedgerTests(TestCase):
    def setUp(self):
        self.pack = ensure_beta_credit_packs()[0]
        self.email = "buyer@example.com"
        self.purchase = Purchase.objects.create(
            email=self.email,
            credit_pack=self.pack,
            amount_cents=self.pack.price_cents,
        )

    def test_beta_pack_prices(self):
        packs = ensure_beta_credit_packs()
        self.assertEqual([(p.credits_included, p.price_cents) for p in packs], [
            (1, 100),
            (2, 190),
            (3, 275),
            (4, 350),
            (5, 400),
        ])

    def test_idempotent_credit_grant(self):
        grant_credits_for_purchase(self.purchase, source_id="cs_test_123")
        grant_credits_for_purchase(self.purchase, source_id="cs_test_123")
        self.assertEqual(get_credit_balance(self.email), 1)
        self.assertEqual(CreditLedgerEntry.objects.count(), 1)

    def test_generation_spends_one_credit(self):
        grant_credits_for_purchase(self.purchase, source_id="cs_test_123")
        song = SongRequest.objects.create(
            email=self.email,
            occasion="birthday",
            recipient_name="Sam",
            relationship="friend",
            personal_details="Sam loves tacos, board games, and arriving fashionably late.",
            vibe="pop_anthem",
            tone="funny",
        )
        job = start_generation(song, provider_name="mock")
        self.assertEqual(job.status, GenerationJobStatus.COMPLETED)
        self.assertEqual(get_credit_balance(self.email), 0)
        self.assertTrue(
            CreditLedgerEntry.objects.filter(entry_type=CreditEntryType.SPEND, amount=-1).exists()
        )
        song.refresh_from_db()
        self.assertEqual(song.status, SongRequestStatus.COMPLETED)

    def test_default_local_generation_uses_mock_provider(self):
        grant_credits_for_purchase(self.purchase, source_id="cs_test_123")
        song = SongRequest.objects.create(
            email=self.email,
            occasion="birthday",
            recipient_name="Sam",
            relationship="friend",
            personal_details="Sam loves tacos, board games, and arriving fashionably late.",
            vibe="pop_anthem",
            tone="funny",
        )
        job = start_generation(song)
        self.assertEqual(job.provider, "mock")
        self.assertEqual(job.status, GenerationJobStatus.COMPLETED)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_generation_queues_job_when_celery_not_eager(self):
        grant_credits_for_purchase(self.purchase, source_id="cs_test_123")
        song = SongRequest.objects.create(
            email=self.email,
            occasion="birthday",
            recipient_name="Sam",
            relationship="friend",
            personal_details="Sam loves tacos, board games, and arriving fashionably late.",
            vibe="pop_anthem",
            tone="funny",
        )
        with patch("apps.generation.tasks.generate_song_task.delay") as delay:
            job = start_generation(song, provider_name="mock")

        delay.assert_called_once_with(job.id)
        self.assertEqual(job.status, GenerationJobStatus.QUEUED)
        self.assertEqual(get_credit_balance(self.email), 0)

    def test_failed_provider_refunds_credit(self):
        grant_credits_for_purchase(self.purchase, source_id="cs_test_123")
        song = SongRequest.objects.create(
            email=self.email,
            occasion="birthday",
            recipient_name="Sam",
            relationship="friend",
            personal_details="Sam loves tacos, board games, and arriving fashionably late.",
            vibe="pop_anthem",
            tone="funny",
        )
        job = start_generation(song, provider_name="elevenlabs")
        self.assertEqual(job.status, GenerationJobStatus.REFUNDED)
        self.assertEqual(get_credit_balance(self.email), 1)
        self.assertTrue(
            CreditLedgerEntry.objects.filter(entry_type=CreditEntryType.REFUND, amount=1).exists()
        )
