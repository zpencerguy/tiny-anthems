from celery import shared_task

from .services import run_generation_job


@shared_task(bind=True, autoretry_for=(), max_retries=0)
def generate_song_task(self, job_id):
    job = run_generation_job(job_id)
    return {"job_id": job.id, "status": job.status}
