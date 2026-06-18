from job.models.job import Job


def create_job(type: str, payload: dict, idempotency_key=None) -> tuple[Job, bool]:

    if idempotency_key:

        from django.db import transaction, IntegrityError
        

        try:
            existing_job = Job.objects.get(idempotency_key=idempotency_key)
            return existing_job, False
        except Job.DoesNotExist:

            try:
                with transaction.atomic():
                    job = Job.objects.create(
                        idempotency_key=idempotency_key,
                        type=type,
                        payload=payload,
                    )
                    return job, True
            except IntegrityError:


                existing_job = Job.objects.get(idempotency_key=idempotency_key)
                return existing_job, False

    job = Job.objects.create(type=type, payload=payload)
    return job, True
