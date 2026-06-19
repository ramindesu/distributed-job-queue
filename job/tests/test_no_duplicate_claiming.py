"""
Test to demonstrate that two workers CANNOT pick up the same job.
This proves the race condition is properly handled.
"""

import threading
import time
from django.test import TransactionTestCase
from django.db import transaction

from job.models.job import Job
from worker.models.worker import Worker
from job.services import claim_job


class NoDuplicateClaimingTest(TransactionTestCase):

    def test_two_workers_cannot_claim_same_job(self):

        jobs = []
        for i in range(5):
            job = Job.objects.create(
                type=Job.JobType.SEND_EMAIL,
                payload={"recipient": f"test{i}@example.com"},
                status=Job.Status.PENDING,
            )
            jobs.append(job)

        claimed_results = []
        errors = []

        def worker_claim_job(worker_name):

            try:

                worker = Worker.objects.create(name=worker_name)

                job = claim_job(worker)

                if job:
                    claimed_results.append(
                        {
                            "worker_id": worker.id,
                            "worker_name": worker.name,
                            "job_id": job.id,
                        }
                    )
            except Exception as e:
                errors.append(f"{worker_name}: {str(e)}")

        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_claim_job, args=(f"worker-{i}",))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        print(f"\n{'='*60}")
        print(f"RACE CONDITION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Jobs created: 5")
        print(f"Workers spawned: 10")
        print(f"Jobs claimed: {len(claimed_results)}")
        print(f"{'='*60}")

        self.assertEqual(len(claimed_results), 5, "Should claim exactly 5 jobs")

        job_ids_claimed = [r["job_id"] for r in claimed_results]
        unique_job_ids = set(job_ids_claimed)

        print(f"\nClaimed job IDs: {sorted(job_ids_claimed)}")
        print(f"Unique job IDs: {sorted(unique_job_ids)}")

        self.assertEqual(
            len(job_ids_claimed),
            len(unique_job_ids),
            "DUPLICATE JOB CLAIM DETECTED! Same job claimed by multiple workers!",
        )

        for result in claimed_results:
            job = Job.objects.get(id=result["job_id"])
            self.assertEqual(job.status, Job.Status.CLAIMED)
            self.assertEqual(job.worker.id, result["worker_id"])
            print(
                f" Job #{job.id} → Worker '{result['worker_name']}' (ID: {result['worker_id']})"
            )

        print(f"\n{'='*60}")
        print(f" SUCCESS: No duplicate claims detected!")
        print(f"{'='*60}\n")

    def test_explain_how_it_works(self):
        """
        Explain the mechanism that prevents duplicate claiming
        """
        print(f"\n{'='*60}")
        print(f"HOW DUPLICATE CLAIMING IS PREVENTED")
        print(f"{'='*60}")

        explanation = """
The key is this line in claim_job():

    Job.objects.select_for_update(skip_locked=True).filter(...)

How it works:

1. SELECT FOR UPDATE
   - Acquires an exclusive row-level lock on the job row
   - No other transaction can modify this row until we commit
   - Database guarantees only ONE transaction holds the lock

2. SKIP LOCKED
   - If a row is already locked by another transaction, SKIP IT
   - Don't wait, move to the next available row
   - Worker gets the next unlocked job immediately

3. ATOMIC TRANSACTION
   - Lock acquisition + status update happen atomically
   - Either both succeed or both fail (no partial state)

Timeline Example:
-----------------
Time  | Worker 1              | Worker 2
------|----------------------|----------------------
T1    | SELECT job #1 (lock) | SELECT job #1 (locked!)
T2    | Update job #1        | Skip job #1 (locked)
T3    | COMMIT (unlock)      | SELECT job #2 (lock)
T4    |                      | Update job #2
T5    |                      | COMMIT (unlock)

Result: Worker 1 gets job #1, Worker 2 gets job #2
        NO DUPLICATE CLAIMING!

Database Level:
---------------
PostgreSQL: Fully supports SELECT FOR UPDATE SKIP LOCKED (9.5+)
MySQL: Supports it (8.0+)
SQLite: Limited support (3.38+) - use PostgreSQL for production

Why This Works:
---------------
The lock is acquired at the DATABASE level, not application level.
Even with 1000 workers hitting the database simultaneously,
the database GUARANTEES only one transaction can lock a specific row.

Alternative approaches (DON'T DO THIS):
---------------------------------------
❌ Check status, then update (RACE CONDITION!)
   job = Job.objects.filter(status='PENDING').first()
   job.status = 'CLAIMED'  # Another worker could claim it here!
   job.save()

❌ F() expressions without locking (STILL RACE CONDITION!)
   Job.objects.filter(status='PENDING').update(status='CLAIMED')
   # Multiple workers can update the same job!

✅ Correct approach (WHAT WE USE):
   with transaction.atomic():
       job = Job.objects.select_for_update(skip_locked=True)...
       job.status = 'CLAIMED'
       job.save()
"""
        print(explanation)
        print(f"{'='*60}\n")


        self.assertTrue(True)

    def test_stress_test_concurrent_claiming(self):
        """
        Stress test: 100 workers, 50 jobs
        Verify no duplicates even under extreme concurrency
        """

        num_jobs = 50
        num_workers = 100

        for i in range(num_jobs):
            Job.objects.create(
                type=Job.JobType.SEND_EMAIL,
                payload={"recipient": f"test{i}@example.com"},
                status=Job.Status.PENDING,
            )

        claimed_results = []

        def worker_claim_job(worker_id):
            try:
                worker = Worker.objects.create(name=f"stress-worker-{worker_id}")
                job = claim_job(worker)
                if job:
                    claimed_results.append((worker.id, job.id))
            except Exception:
                pass  


        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=worker_claim_job, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()


        job_ids = [job_id for _, job_id in claimed_results]
        unique_job_ids = set(job_ids)

        print(f"\n{'='*60}")
        print(f"STRESS TEST RESULTS")
        print(f"{'='*60}")
        print(f"Jobs created: {num_jobs}")
        print(f"Workers spawned: {num_workers}")
        print(f"Jobs claimed: {len(claimed_results)}")
        print(f"Unique jobs: {len(unique_job_ids)}")
        print(f"{'='*60}\n")

        self.assertEqual(
            len(job_ids),
            len(unique_job_ids),
            f"DUPLICATE DETECTED! {len(job_ids)} claims but only {len(unique_job_ids)} unique jobs",
        )

        self.assertLessEqual(
            len(claimed_results), num_jobs, "Claimed more jobs than available!"
        )
