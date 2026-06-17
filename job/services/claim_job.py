from django.db import transaction
from django.utils import timezone
from job.models.job import Job
from worker.models.worker import Worker


def claim_job(worker: Worker) -> Job | None:
    with transaction.atomic():
        job = (
            Job.objects.select_for_update(skip_locked=True)
            .filter(status=Job.Status.PENDING)
            .order_by("created_at")
            .first()
        )
        if not job:
            return None
        job.status = Job.Status.CLAIMED
        job.worker = worker
        job.claimed_at = timezone.now()

        job.save(update_fields=["status", "worker", "claimed_at"])
        return job
