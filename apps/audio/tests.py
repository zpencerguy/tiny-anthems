from pathlib import Path

from django.test import TestCase

from .services import get_audio_duration_seconds


class AudioDurationTests(TestCase):
    def test_mp3_duration_is_detected_without_ffprobe(self):
        audio_path = Path("static/audio/samples/hero-sarah-birthday-banger.mp3")
        duration = get_audio_duration_seconds(audio_path.read_bytes(), "audio/mpeg")

        self.assertGreater(duration, 14)
        self.assertLess(duration, 16)
