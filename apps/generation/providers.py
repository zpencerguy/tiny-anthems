from dataclasses import dataclass, field
from typing import Protocol
import json
import math
import struct
import wave
from io import BytesIO

import requests


class MusicProviderError(RuntimeError):
    def __init__(self, message, *, status_code=None, error_code="", response_body=""):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


@dataclass
class MusicGenerationRequest:
    prompt: str
    duration_seconds: int
    vibe: str
    tone: str
    lyrics: str = ""
    instrumental_only: bool = False
    family_friendly: bool = True
    seed: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class MusicGenerationResult:
    audio_bytes: bytes
    mime_type: str
    provider_request_id: str
    duration_seconds: float
    metadata: dict = field(default_factory=dict)
    cost_units: float | None = None


class MusicGenerationProvider(Protocol):
    name: str

    def generate(self, request: MusicGenerationRequest) -> MusicGenerationResult:
        ...


class MockMusicProvider:
    name = "mock"

    def generate(self, request: MusicGenerationRequest) -> MusicGenerationResult:
        audio_bytes = self._build_tone_wav(duration_seconds=request.duration_seconds)
        return MusicGenerationResult(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            provider_request_id="mock-local",
            duration_seconds=request.duration_seconds,
            metadata={"mock": True},
            cost_units=0,
        )

    def _build_tone_wav(self, duration_seconds):
        sample_rate = 22050
        amplitude = 0.25
        frames = int(sample_rate * duration_seconds)
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            for index in range(frames):
                envelope = min(index / 800, 1, (frames - index) / 800)
                frequency = 440 if index < frames / 2 else 554.37
                sample = amplitude * envelope * math.sin(2 * math.pi * frequency * index / sample_rate)
                wav.writeframes(struct.pack("<h", int(sample * 32767)))
        return buffer.getvalue()


class ElevenLabsMusicProvider:
    name = "elevenlabs"
    api_url = "https://api.elevenlabs.io/v1/music"
    plan_url = "https://api.elevenlabs.io/v1/music/plan"

    def __init__(
        self,
        api_key,
        *,
        model_id="music_v1",
        output_format="mp3_44100_128",
        timeout_seconds=180,
        use_composition_plan=False,
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.output_format = output_format
        self.timeout_seconds = timeout_seconds
        self.use_composition_plan = use_composition_plan

    def generate(self, request: MusicGenerationRequest) -> MusicGenerationResult:
        if not self.api_key:
            raise MusicProviderError(
                "ELEVENLABS_API_KEY is not configured.", error_code="missing_api_key"
            )

        self._validate_request(request)
        payload = self._build_compose_payload(request)
        metadata = {
            "provider": self.name,
            "model_id": self.model_id,
            "output_format": self.output_format,
            "prompt_length": len(request.prompt),
            "music_length_ms": request.duration_seconds * 1000,
            "used_composition_plan": False,
        }

        if self.use_composition_plan:
            composition_plan = self.create_composition_plan(request)
            payload = {
                "composition_plan": composition_plan,
                "model_id": self.model_id,
                "respect_sections_durations": True,
            }
            metadata["used_composition_plan"] = True

        response = requests.post(
            self.api_url,
            params={"output_format": self.output_format},
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_seconds,
        )
        self._raise_for_error(response, "compose_failed")
        song_id = response.headers.get("song-id", "")
        metadata.update(
            {
                "status_code": response.status_code,
                "song_id": song_id,
                "content_type": response.headers.get("content-type", ""),
            }
        )
        return MusicGenerationResult(
            audio_bytes=response.content,
            mime_type=response.headers.get("content-type", "audio/mpeg").split(";")[0],
            provider_request_id=song_id,
            duration_seconds=request.duration_seconds,
            metadata=metadata,
        )

    def create_composition_plan(self, request: MusicGenerationRequest):
        response = requests.post(
            self.plan_url,
            headers=self._headers(),
            json={
                "prompt": request.prompt,
                "music_length_ms": request.duration_seconds * 1000,
                "model_id": self.model_id,
            },
            timeout=self.timeout_seconds,
        )
        self._raise_for_error(response, "composition_plan_failed")
        return response.json()

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

    def _build_compose_payload(self, request: MusicGenerationRequest):
        payload = {
            "prompt": request.prompt,
            "music_length_ms": request.duration_seconds * 1000,
            "model_id": self.model_id,
            "force_instrumental": request.instrumental_only,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    def _validate_request(self, request: MusicGenerationRequest):
        if not request.prompt.strip():
            raise MusicProviderError("Music prompt is required.", error_code="empty_prompt")
        if len(request.prompt) > 4100:
            raise MusicProviderError(
                "Music prompt is longer than ElevenLabs allows.",
                error_code="prompt_too_long",
            )
        if not 3 <= request.duration_seconds <= 600:
            raise MusicProviderError(
                "Music duration must be between 3 and 600 seconds.",
                error_code="invalid_duration",
            )

    def _raise_for_error(self, response, error_code):
        if response.status_code < 400:
            return
        response_body = self._response_body(response)
        raise MusicProviderError(
            f"ElevenLabs music API request failed with HTTP {response.status_code}.",
            status_code=response.status_code,
            error_code=error_code,
            response_body=response_body,
        )

    def _response_body(self, response):
        try:
            return json.dumps(response.json())[:2000]
        except ValueError:
            return response.text[:2000]
