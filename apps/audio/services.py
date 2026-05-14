import subprocess
import tempfile
import wave
from io import BytesIO
from pathlib import Path


class AudioValidationError(RuntimeError):
    def __init__(self, message, *, error_code="audio_validation_failed"):
        super().__init__(message)
        self.error_code = error_code


def get_audio_duration_seconds(audio_bytes, mime_type):
    if not audio_bytes:
        raise AudioValidationError("Generated audio file is empty.", error_code="empty_audio")

    if mime_type in {"audio/wav", "audio/x-wav", "audio/wave"}:
        return _get_wav_duration_seconds(audio_bytes)

    return _get_duration_with_ffprobe(audio_bytes, mime_type)


def validate_audio_duration(audio_bytes, mime_type, requested_duration_seconds):
    actual_duration = get_audio_duration_seconds(audio_bytes, mime_type)
    minimum_duration = max(1, requested_duration_seconds - 1)
    if actual_duration < minimum_duration:
        raise AudioValidationError(
            (
                f"Generated audio is too short: {actual_duration:.2f}s returned, "
                f"expected at least {minimum_duration:.2f}s."
            ),
            error_code="audio_too_short",
        )
    return actual_duration


def _get_wav_duration_seconds(audio_bytes):
    try:
        with wave.open(BytesIO(audio_bytes), "rb") as wav:
            frame_rate = wav.getframerate()
            if frame_rate <= 0:
                raise AudioValidationError("Generated WAV has invalid frame rate.")
            return wav.getnframes() / frame_rate
    except wave.Error as exc:
        raise AudioValidationError(f"Generated WAV is invalid: {exc}") from exc


def _get_duration_with_ffprobe(audio_bytes, mime_type):
    suffix = _suffix_for_mime_type(mime_type)
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        temp_file.write(audio_bytes)
        temp_file.flush()
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    temp_file.name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise AudioValidationError(f"Could not inspect generated audio duration: {exc}") from exc

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise AudioValidationError("Generated audio duration could not be parsed.") from exc


def _suffix_for_mime_type(mime_type):
    return {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/wave": ".wav",
    }.get(mime_type, Path(mime_type).suffix or ".audio")
