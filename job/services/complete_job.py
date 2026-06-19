from django.utils import timezone
from django.db import transaction

from job.models.job import Job


def complete_job(job: Job) -> Job:
    with transaction.atomic():

        job = Job.objects.select_for_update().get(pk=job.pk)
        
        if job.status != Job.Status.RUNNING:
            raise ValueError(f"Job must be RUNNING to complete. Current status: {job.status}")

        job.status = Job.Status.COMPLETED
        job.completed_at = timezone.now()

        job.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        return job
