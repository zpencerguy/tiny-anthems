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
