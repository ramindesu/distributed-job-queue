import time
from django.utils import timezone
from django.db import transaction

from job.models.job import Job
from job.models.job_execution import JobExecution
from .start_job import start_job
from .complete_job import complete_job
from .fail_job import fail_job


def execute_job(job: Job) -> Job:


    execution = JobExecution.objects.create(
        job=job,
        worker=job.worker,
        status=JobExecution.Status.RUNNING,
        started_at=timezone.now(),
    )
    
    try:

        job = start_job(job)
        

        result = _execute_job_logic(job)
        

        job = complete_job(job)
        

        execution.status = JobExecution.Status.COMPLETED
        execution.finished_at = timezone.now()
        execution.result = result
        execution.save(update_fields=["status", "finished_at", "result"])
        
        return job
        
    except Exception as e:

        error_message = str(e)
        

        job = fail_job(job, error_message=error_message)
        

        execution.status = JobExecution.Status.FAILED
        execution.finished_at = timezone.now()
        execution.error_message = error_message
        execution.save(update_fields=["status", "finished_at", "error_message"])
        
        return job


def _execute_job_logic(job: Job) -> dict:

    payload = job.payload
    
    if job.type == Job.JobType.SEND_EMAIL:

        time.sleep(1)  
        return {
            "email_sent": True,
            "recipient": payload.get("recipient"),
            "subject": payload.get("subject"),
        }
    
    elif job.type == Job.JobType.GENERATE_REPORT:

        time.sleep(2)  
        return {
            "report_generated": True,
            "report_type": payload.get("report_type"),
            "record_count": payload.get("record_count", 0),
        }
    
    elif job.type == Job.JobType.RESERVE_TICKET:

        time.sleep(1.5)  
        

        import random
        if random.random() < 0.1:  
            raise Exception("Ticket reservation service temporarily unavailable")
        
        return {
            "ticket_reserved": True,
            "ticket_id": payload.get("ticket_id"),
            "seat_number": payload.get("seat_number"),
        }
    
    else:
        raise ValueError(f"Unknown job type: {job.type}")
