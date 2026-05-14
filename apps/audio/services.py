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
    if mime_type in {"audio/mpeg", "audio/mp3"}:
        return _get_mp3_duration_seconds(audio_bytes)

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


def _get_mp3_duration_seconds(audio_bytes):
    offset = _skip_id3v2_tag(audio_bytes)
    duration = 0.0
    frame_count = 0

    while offset + 4 <= len(audio_bytes):
        header = int.from_bytes(audio_bytes[offset : offset + 4], "big")
        frame = _parse_mp3_frame_header(header)
        if frame is None:
            offset += 1
            continue

        frame_length, samples_per_frame, sample_rate = frame
        if frame_length <= 0:
            offset += 1
            continue
        duration += samples_per_frame / sample_rate
        frame_count += 1
        offset += frame_length

    if frame_count == 0:
        raise AudioValidationError("Generated MP3 has no valid audio frames.")
    return duration


def _skip_id3v2_tag(audio_bytes):
    if len(audio_bytes) < 10 or audio_bytes[:3] != b"ID3":
        return 0
    size = 0
    for byte in audio_bytes[6:10]:
        size = (size << 7) | (byte & 0x7F)
    footer_size = 10 if audio_bytes[5] & 0x10 else 0
    return 10 + size + footer_size


def _parse_mp3_frame_header(header):
    if (header & 0xFFE00000) != 0xFFE00000:
        return None

    version_bits = (header >> 19) & 0b11
    layer_bits = (header >> 17) & 0b11
    bitrate_index = (header >> 12) & 0b1111
    sample_rate_index = (header >> 10) & 0b11
    padding = (header >> 9) & 0b1

    if version_bits == 0b01 or layer_bits != 0b01:
        return None
    if bitrate_index in {0, 0b1111} or sample_rate_index == 0b11:
        return None

    if version_bits == 0b11:
        sample_rates = [44100, 48000, 32000]
        bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
        samples_per_frame = 1152
        frame_length = int((144000 * bitrates[bitrate_index]) / sample_rates[sample_rate_index] + padding)
    else:
        sample_rates = {
            0b10: [22050, 24000, 16000],
            0b00: [11025, 12000, 8000],
        }[version_bits]
        bitrates = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
        samples_per_frame = 576
        frame_length = int((72000 * bitrates[bitrate_index]) / sample_rates[sample_rate_index] + padding)

    return frame_length, samples_per_frame, sample_rates[sample_rate_index]


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
