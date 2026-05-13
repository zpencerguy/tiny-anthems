from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.billing.services import refund_credit, spend_credit
from apps.songs.models import ModerationStatus, SongRequestStatus
from apps.storage.models import SongAsset

from .models import GenerationJob, GenerationJobStatus
from .providers import ElevenLabsMusicProvider, MockMusicProvider, MusicGenerationRequest


def build_music_prompt(song_request):
    vibe = song_request.get_vibe_display()
    tone = song_request.get_tone_display()
    prompt = f"""Create a {song_request.requested_duration_seconds}-second personalized {vibe} mini-song.

Recipient: {song_request.recipient_name}.
Nickname: {song_request.recipient_nickname or "none"}.
Occasion: {song_request.get_occasion_display()} {song_request.milestone}.
Relationship: {song_request.get_relationship_display()}.
Tone: {tone}.
Details to include: {song_request.personal_details}.
Avoid: {song_request.things_to_avoid or "mean insults, explicit lyrics, copyrighted lyrics, artist imitation"}.

The song should feel like a catchy tiny anthem, not a full song. Include the recipient's name clearly. Make the lyrics original. Do not imitate any specific artist or existing song. Use a fun chorus-like hook and end cleanly."""
    return prompt.strip()


def get_provider(name=None):
    provider_name = name or settings.DEFAULT_MUSIC_PROVIDER
    if provider_name == "mock":
        return MockMusicProvider()
    if provider_name == "elevenlabs":
        return ElevenLabsMusicProvider(settings.ELEVENLABS_API_KEY)
    return MockMusicProvider()


def start_generation(song_request, provider_name=None):
    attempt = song_request.generation_jobs.count() + 1
    job = GenerationJob.objects.create(
        song_request=song_request,
        user=song_request.user,
        provider=provider_name or settings.DEFAULT_MUSIC_PROVIDER,
        attempt_number=attempt,
        prompt=build_music_prompt(song_request),
    )
    spend_credit(song_request.email, song_request, job)
    song_request.status = SongRequestStatus.QUEUED
    song_request.moderation_status = ModerationStatus.APPROVED
    song_request.prompt_used = job.prompt
    song_request.save(update_fields=["status", "moderation_status", "prompt_used", "updated_at"])
    return run_generation_job(job)


def run_generation_job(job):
    job.status = GenerationJobStatus.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])
    song = job.song_request
    song.status = SongRequestStatus.GENERATING
    song.save(update_fields=["status", "updated_at"])

    try:
        provider = get_provider(job.provider)
        result = provider.generate(
            MusicGenerationRequest(
                prompt=job.prompt,
                duration_seconds=song.requested_duration_seconds,
                vibe=song.vibe,
                tone=song.tone,
                family_friendly=song.family_friendly,
            )
        )
        extension = "mp3" if result.mime_type == "audio/mpeg" else "wav"
        filename = f"song-{song.id}-job-{job.id}.{extension}"
        job.raw_audio_file.save(filename, ContentFile(result.audio_bytes), save=False)
        job.processed_audio_file.save(filename, ContentFile(result.audio_bytes), save=False)
        job.provider_request_id = result.provider_request_id
        job.provider_response_metadata = result.metadata
        job.provider_cost_units = result.cost_units
        job.duration_seconds = result.duration_seconds or song.requested_duration_seconds
        job.status = GenerationJobStatus.COMPLETED
        job.completed_at = timezone.now()
        job.save()
        SongAsset.objects.create(
            song_request=song,
            generation_job=job,
            asset_type="final_mp3",
            storage_key=job.processed_audio_file.name,
            mime_type=result.mime_type,
            duration_seconds=job.duration_seconds,
            metadata={"provider": job.provider},
        )
        song.status = SongRequestStatus.COMPLETED
        song.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        job.status = GenerationJobStatus.REFUNDED
        job.error_code = exc.__class__.__name__
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save()
        refund_credit(song.email, song, job, str(exc))
        song.status = SongRequestStatus.FAILED
        song.save(update_fields=["status", "updated_at"])
    return job
