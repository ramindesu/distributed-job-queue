from django.utils import timezone
from django.db import transaction

from job.models.job import Job


def fail_job(job: Job, error_message: str = "") -> Job:

    with transaction.atomic():

        job = Job.objects.select_for_update().get(pk=job.pk)
        
        if job.status not in [Job.Status.CLAIMED, Job.Status.RUNNING]:
            raise ValueError(
                f"Job must be CLAIMED or RUNNING to fail. Current status: {job.status}"
            )
        

        job.retry_count += 1
        

        if job.retry_count < job.max_retries:

            job.status = Job.Status.PENDING
            job.worker = None
            job.claimed_at = None
            job.started_at = None
            
            job.save(
                update_fields=[
                    "status",
                    "retry_count",
                    "worker",
                    "claimed_at",
                    "started_at",
                ]
            )
        else:

            job.status = Job.Status.FAILED
            job.completed_at = timezone.now()
            
            job.save(
                update_fields=[
                    "status",
                    "retry_count",
                    "completed_at",
                ]
            )
        
        return job
