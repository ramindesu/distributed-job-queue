from django.db import transaction
from django.utils import timezone

from job.models.job import Job
from worker.models.worker import Worker
from .claim_job import claim_job
from .execute_job import execute_job


def process_next_job(worker: Worker) -> Job | None:

    _reclaim_expired_jobs()

    _reclaim_stuck_jobs()

    job = claim_job(worker)

    if not job:
        return None

    try:
        job = execute_job(job)
        return job
    except Exception as e:

        print(f"Critical error processing job {job.id}: {e}")
        return job


def _reclaim_expired_jobs():

    with transaction.atomic():

        expired_jobs = Job.objects.select_for_update(skip_locked=True).filter(
            status=Job.Status.CLAIMED,
            claimed_at__lt=timezone.now() - timezone.timedelta(minutes=5),
        )

        for job in expired_jobs:
            job.status = Job.Status.PENDING
            job.worker = None
            job.claimed_at = None
            job.save(update_fields=["status", "worker", "claimed_at"])


def _reclaim_stuck_jobs():

    with transaction.atomic():

        running_jobs = Job.objects.select_for_update(skip_locked=True).filter(
            status=Job.Status.RUNNING,
        )

        for job in running_jobs:

            if not job.execution_expired:
                continue

            job.retry_count += 1

            if job.retry_count < job.max_retries:

                job.status = Job.Status.PENDING
                job.worker = None
                job.started_at = None
                job.claimed_at = None
            else:

                job.status = Job.Status.FAILED
                job.completed_at = timezone.now()

            job.save(
                update_fields=[
                    "status",
                    "retry_count",
                    "worker",
                    "started_at",
                    "claimed_at",
                    "completed_at",
                ]
            )
