# Tiny Anthems

Tiny Anthems is a Django-template private beta app for selling credits and generating short personalized songs.

## Local Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py createsuperuser
python manage.py runserver
```

For local testing, SQLite is used by default. Configure Stripe price IDs and webhooks with the variables in `.env.example` before running checkout against Stripe test mode.

## Music Generation

Local development defaults to the mock provider when `DEBUG=true` and `DEFAULT_MUSIC_PROVIDER` is unset. To call ElevenLabs in a beta/staging environment, set:

```bash
DEFAULT_MUSIC_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=replace-with-real-key
ELEVENLABS_MODEL_ID=music_v1
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128
ELEVENLABS_TIMEOUT_SECONDS=180
ELEVENLABS_USE_COMPOSITION_PLAN=false
```

`ELEVENLABS_USE_COMPOSITION_PLAN=true` will first call `/v1/music/plan`, then submit that plan to `/v1/music`. Leave it off for the simplest prompt-to-song path.
