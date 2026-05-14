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

By default, Docker is configured for the real ElevenLabs provider. Copy the template and add local secrets:

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker`:

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

### GCS Audio Storage

Local development defaults to filesystem storage in `media/`. For beta/staging, use Google Cloud Storage so generated songs do not accumulate inside the app container:

```bash
STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=tiny-anthems-audio
GCS_PROJECT_ID=your-gcp-project-id
GCS_SIGNED_URL_TTL_SECONDS=900
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-service-account.json
```

Keep the service account JSON outside Git at `secrets/gcp-service-account.json`, then start Docker Compose with the GCS override:

```bash
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.gcs.yml up --build
```

The app stores private object keys in the database and serves downloads through short-lived signed URLs after validating the song or share token.

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

Tiny Anthems defaults to ElevenLabs for generation. To call ElevenLabs in a beta/staging environment, set:

```bash
DEFAULT_MUSIC_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=replace-with-real-key
ELEVENLABS_MODEL_ID=music_v1
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128
ELEVENLABS_TIMEOUT_SECONDS=180
ELEVENLABS_USE_COMPOSITION_PLAN=false
```

`ELEVENLABS_USE_COMPOSITION_PLAN=true` will first call `/v1/music/plan`, then submit that plan to `/v1/music`. Leave it off for the simplest prompt-to-song path.

There is still a mock provider for automated tests and local development only. It is disabled unless explicitly enabled:

```bash
ALLOW_MOCK_MUSIC_PROVIDER=true
DEFAULT_MUSIC_PROVIDER=mock
```
