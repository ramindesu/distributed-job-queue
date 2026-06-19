#!/usr/bin/env python
"""
Example usage of the distributed job queue system.
Run this after starting the Django server and workers.
"""

import os
import django
import time
import uuid
# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from job.models.job import Job
from job.services import create_job
from worker.models.worker import Worker


def example_1_create_simple_jobs():
    """Create multiple simple jobs"""
    print("\n=== Example 1: Creating Simple Jobs ===")
    
    for i in range(5):
        job, created = create_job(
            type=Job.JobType.SEND_EMAIL,
            payload={
                "recipient": f"user{i}@example.com",
                "subject": f"Test Email {i}",
                "body": "This is a test email"
            }
        )
        print(f"Created job #{job.id}: {job.type}")
    
    print(f"\nTotal pending jobs: {Job.objects.filter(status=Job.Status.PENDING).count()}")


def example_2_idempotent_jobs():
    """Demonstrate idempotent job creation"""
    print("\n=== Example 2: Idempotent Job Creation ===")
    
    idempotency_key = str(uuid.uuid4())
    
    # First request - should create
    job1, created1 = create_job(
        type=Job.JobType.RESERVE_TICKET,
        payload={
            "ticket_id": "TKT-12345",
            "seat_number": "A23"
        },
        idempotency_key=idempotency_key
    )
    print(f"First request: Job #{job1.id}, Created: {created1}")
    
    # Second request with same key - should return existing
    job2, created2 = create_job(
        type=Job.JobType.RESERVE_TICKET,
        payload={
            "ticket_id": "TKT-12345",
            "seat_number": "A23"
        },
        idempotency_key=idempotency_key
    )
    print(f"Second request: Job #{job2.id}, Created: {created2}")
    print(f"Same job? {job1.id == job2.id}")


def example_3_check_job_status():
    """Check status of jobs"""
    print("\n=== Example 3: Job Status ===")
    
    status_counts = {}
    for status in Job.Status:
        count = Job.objects.filter(status=status).count()
        status_counts[status.label] = count
    
    for status, count in status_counts.items():
        print(f"{status}: {count}")


def example_4_worker_status():
    """Check worker status"""
    print("\n=== Example 4: Worker Status ===")
    
    workers = Worker.objects.all()
    
    if not workers:
        print("No workers registered")
    else:
        for worker in workers:
            status = "🟢 ALIVE" if worker.is_alive else "🔴 DEAD"
            print(f"{worker.name}: {status} (Last heartbeat: {worker.last_heartbeat})")


def example_5_job_with_retries():
    """Create jobs that may fail and retry"""
    print("\n=== Example 5: Jobs with Retry Logic ===")
    
    # Create jobs that might fail
    for i in range(3):
        job, created = create_job(
            type=Job.JobType.RESERVE_TICKET,
            payload={
                "ticket_id": f"TKT-{i}",
                "seat_number": f"B{i}"
            }
        )
        print(f"Created job #{job.id} with max_retries={job.max_retries}")


def example_6_execution_history():
    """Show execution history for jobs"""
    print("\n=== Example 6: Execution History ===")
    
    from job.models.job_execution import JobExecution
    
    # Get completed jobs
    completed_jobs = Job.objects.filter(
        status__in=[Job.Status.COMPLETED, Job.Status.FAILED]
    )[:5]
    
    for job in completed_jobs:
        print(f"\nJob #{job.id} ({job.type}) - Status: {job.status}")
        executions = JobExecution.objects.filter(job=job)
        
        for execution in executions:
            print(f"  Attempt #{execution.id}: {execution.status}")
            if execution.error_message:
                print(f"    Error: {execution.error_message}")
            if execution.result:
                print(f"    Result: {execution.result}")


def main():
    """Run all examples"""
    print("=" * 60)
    print("Distributed Job Queue - Usage Examples")
    print("=" * 60)
    
    # Run examples
    example_1_create_simple_jobs()
    time.sleep(1)
    
    example_2_idempotent_jobs()
    time.sleep(1)
    
    example_3_check_job_status()
    time.sleep(1)
    
    example_4_worker_status()
    time.sleep(1)
    
    example_5_job_with_retries()
    time.sleep(1)
    
    # Wait a bit for jobs to be processed
    print("\n" + "=" * 60)
    print("Waiting 10 seconds for workers to process jobs...")
    print("=" * 60)
    time.sleep(10)
    
    example_3_check_job_status()
    example_6_execution_history()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
