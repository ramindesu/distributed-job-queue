from django.utils import timezone

from job.models.job import Job


def complete_job(job: Job) -> Job:
    if job.status != Job.Status.RUNNING:
        raise ValueError("job must be at running level ")

    job.status = Job.Status.COMPLETED
    job.completed_at = timezone.now()

    job.save(
        update_fields=[
            "status",
            "completed_at",
        ]
    )

    return job