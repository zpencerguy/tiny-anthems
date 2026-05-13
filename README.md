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

## Docker Compose Setup

Start the app stack:

```bash
docker compose up --build
```

The app runs at `http://localhost:8000` with:

- Django web server
- Celery worker
- Postgres
- Redis

By default, Docker uses `.env.docker.example` and `DEFAULT_MUSIC_PROVIDER=mock` so you can test the async pipeline without spending API credits. For local secrets or overrides, copy the template:

```bash
cp .env.docker.example .env.docker
```

To test real ElevenLabs generation, edit `.env.docker`:

```bash
DEFAULT_MUSIC_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=replace-with-real-key
CELERY_TASK_ALWAYS_EAGER=false
```

Then restart:

```bash
docker compose --env-file .env.docker up --build
```

Never commit `.env.docker`; it is ignored by Git.

## Background Jobs

Generation is queued through Celery. Local development defaults to eager execution so a separate worker is not required:

```bash
CELERY_TASK_ALWAYS_EAGER=true
```

For production-like async behavior, run Redis and set `CELERY_TASK_ALWAYS_EAGER=false`, then start a worker:

```bash
celery -A config worker -l info
```

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
