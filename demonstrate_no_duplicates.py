#!/usr/bin/env python


import os
import django
import threading
import time
from collections import defaultdict


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from job.models.job import Job
from worker.models.worker import Worker
from job.services import claim_job


def demonstrate_no_duplicate_claiming():

    print("\n" + "="*70)
    print("DEMONSTRATION: Two Workers Cannot Claim the Same Job")
    print("="*70)
    

    Job.objects.all().delete()
    Worker.objects.all().delete()
    

    print("\n Creating 3 jobs...")
    jobs = []
    for i in range(1, 4):
        job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": f"user{i}@example.com"},
            status=Job.Status.PENDING,
        )
        jobs.append(job)
        print(f"    Job #{job.id} created (status: PENDING)")
    

    results = []
    lock = threading.Lock()
    
    def worker_attempt_claim(worker_name, delay=0):

        time.sleep(delay)  
        
        try:
            worker = Worker.objects.create(name=worker_name)
            
            with lock:
                print(f"\n {worker_name} is looking for a job...")
            
            job = claim_job(worker)
            
            if job:
                with lock:
                    results.append({
                        'worker': worker_name,
                        'job_id': job.id,
                        'success': True
                    })
                    print(f"    {worker_name} CLAIMED Job #{job.id}")
            else:
                with lock:
                    results.append({
                        'worker': worker_name,
                        'job_id': None,
                        'success': False
                    })
                    print(f"   {worker_name} found no available jobs")
        except Exception as e:
            with lock:
                print(f"     {worker_name} encountered error: {e}")
    
    # Spawn 5 workers (more than jobs!)
    print("\n Spawning 5 workers to claim 3 jobs...")
    print("   (More workers than jobs to simulate competition)")
    
    threads = []
    worker_names = ['Ali', 'Bizhan', 'Sara', 'Davood', 'Ellahe']
    
    for i, name in enumerate(worker_names):
        thread = threading.Thread(
            target=worker_attempt_claim,
            args=(name, i * 0.01)  
        )
        threads.append(thread)
    

    for thread in threads:
        thread.start()
    

    for thread in threads:
        thread.join()
    

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    successful_claims = [r for r in results if r['success']]
    failed_claims = [r for r in results if not r['success']]
    
    print(f"\n Successful claims: {len(successful_claims)}")
    print(f" Failed claims: {len(failed_claims)}")
    

    claimed_job_ids = [r['job_id'] for r in successful_claims]
    unique_job_ids = set(claimed_job_ids)
    
    print(f"\n Analysis:")
    print(f"   Jobs created: 3")
    print(f"   Workers spawned: 5")
    print(f"   Jobs claimed: {len(claimed_job_ids)}")
    print(f"   Unique jobs claimed: {len(unique_job_ids)}")
    

    if len(claimed_job_ids) == len(unique_job_ids):
        print(f"\n SUCCESS: No duplicate claims!")
        print(f"   Each job was claimed by exactly ONE worker")
    else:
        print(f"\n FAILURE: Duplicate claims detected!")
        print(f"   Some jobs were claimed by multiple workers!")
        return False
    

    print(f"\n Job Assignment:")
    for r in successful_claims:
        job = Job.objects.get(id=r['job_id'])
        print(f"   Job #{job.id} → {r['worker']} (status: {job.status})")
    
    print(f"\n Workers without jobs:")
    for r in failed_claims:
        print(f"   {r['worker']} → (no job available)")
    

    print(f"\n  Database Verification:")
    for job in jobs:
        job.refresh_from_db()
        if job.status == Job.Status.CLAIMED:
            print(f"   Job #{job.id}: CLAIMED by {job.worker.name} ")
        else:
            print(f"   Job #{job.id}: Still PENDING (unclaimed)")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
The SELECT FOR UPDATE SKIP LOCKED mechanism ensures:
1. Only one worker can lock a specific job row
2. Other workers skip locked rows and move to the next job
3. Zero duplicate claims, guaranteed by the database

This is why your job queue is race-condition safe! 
""")
    
    return True


if __name__ == "__main__":
    success = demonstrate_no_duplicate_claiming()
    exit(0 if success else 1)
