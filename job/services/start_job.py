from django.utils import timezone
from django.db import transaction

from job.models.job import Job


def start_job(job: Job) -> Job:
    with transaction.atomic():

        job = Job.objects.select_for_update().get(pk=job.pk)
        
        if job.status != Job.Status.CLAIMED:
            raise ValueError(f"Job must be CLAIMED to start. Current status: {job.status}")
        
        job.status = Job.Status.RUNNING
        job.started_at = timezone.now()

        job.save(
            update_fields=[
                "status",
                "started_at",
            ]
        )

        return job
