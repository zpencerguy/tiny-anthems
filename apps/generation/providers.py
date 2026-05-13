from dataclasses import dataclass, field
from typing import Protocol
import base64

import requests


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
        wav_header = base64.b64decode(
            "UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="
        )
        return MusicGenerationResult(
            audio_bytes=wav_header,
            mime_type="audio/wav",
            provider_request_id="mock-local",
            duration_seconds=0,
            metadata={"mock": True},
            cost_units=0,
        )


class ElevenLabsMusicProvider:
    name = "elevenlabs"
    api_url = "https://api.elevenlabs.io/v1/music"

    def __init__(self, api_key):
        self.api_key = api_key

    def generate(self, request: MusicGenerationRequest) -> MusicGenerationResult:
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured.")

        response = requests.post(
            self.api_url,
            params={"output_format": "mp3_44100_128"},
            headers={
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
            },
            json={
                "prompt": request.prompt,
                "music_length_ms": request.duration_seconds * 1000,
                "model_id": "music_v1",
                "force_instrumental": request.instrumental_only,
            },
            timeout=180,
        )
        response.raise_for_status()
        return MusicGenerationResult(
            audio_bytes=response.content,
            mime_type=response.headers.get("content-type", "audio/mpeg").split(";")[0],
            provider_request_id=response.headers.get("song-id", ""),
            duration_seconds=request.duration_seconds,
            metadata={
                "status_code": response.status_code,
                "song_id": response.headers.get("song-id", ""),
                "provider": self.name,
            },
        )
