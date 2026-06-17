from job.models.job import Job


def create_job(type: str, payload: dict, idempotency_key=None) -> tuple[Job, bool]:

    if idempotency_key:
        return Job.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={"type": type, "payload": payload},
        )

    job = Job.objects.create(type=type, payload=payload)
    return job, True
