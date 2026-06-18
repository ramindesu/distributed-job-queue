from django.utils import timezone

from job.models.job import Job


def start_job(job: Job) -> Job:
    if job.status != Job.Status.CLAIMED:
        raise ValueError("must be claimed first")
    job.status = Job.Status.RUNNING
    job.started_at = timezone.now()

    job.save(
        update_fields=[
            "status",
            "started_at",
        ]
    )

    return job