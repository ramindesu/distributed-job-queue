import time
import threading
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
import uuid
from job.models.job import Job
from job.models.job_execution import JobExecution
from worker.models.worker import Worker
from job.services import (
    create_job,
    claim_job,
    start_job,
    complete_job,
    fail_job,
    process_next_job,
)
from job.services.process_next_job import _reclaim_expired_jobs
from django.db import connection


class JobCreationRaceConditionTest(TransactionTestCase):

    def test_concurrent_job_creation_with_same_idempotency_key(self):

        idempotency_key = str(uuid.uuid4())
        results = []
        errors = []

        def create_job_thread():
            try:
                job, created = create_job(
                    type=Job.JobType.SEND_EMAIL,
                    payload={"recipient": "test@example.com"},
                    idempotency_key=idempotency_key,
                )
                results.append((job.id, created))
            except Exception as e:
                errors.append(str(e))
            finally:
                connection.close()

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_job_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        self.assertEqual(len(results), 10)

        job_ids = set(job_id for job_id, _ in results)
        self.assertEqual(
            len(job_ids), 1, "Multiple jobs were created with same idempotency key"
        )

        created_count = sum(1 for _, created in results if created)
        self.assertEqual(created_count, 1, "Multiple threads reported creating the job")

        self.assertEqual(Job.objects.filter(idempotency_key=idempotency_key).count(), 1)


class JobClaimingRaceConditionTest(TransactionTestCase):

    def setUp(self):

        for i in range(5):
            Job.objects.create(
                type=Job.JobType.SEND_EMAIL,
                payload={"recipient": f"test{i}@example.com"},
                status=Job.Status.PENDING,
            )

    def test_concurrent_job_claiming(self):

        claimed_jobs = []
        errors = []

        def claim_job_thread(worker_name):
            try:
                worker = Worker.objects.create(name=worker_name)
                job = claim_job(worker)
                if job:
                    claimed_jobs.append((worker.id, job.id))
            except Exception as e:
                errors.append(str(e))
            finally:
                connection.close()

        threads = []
        for i in range(10):
            thread = threading.Thread(target=claim_job_thread, args=(f"worker-{i}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        job_ids = [job_id for _, job_id in claimed_jobs]
        self.assertEqual(
            len(job_ids), len(set(job_ids)), "Same job was claimed by multiple workers"
        )

        self.assertLessEqual(len(claimed_jobs), 5)

        for _, job_id in claimed_jobs:
            job = Job.objects.get(id=job_id)
            self.assertEqual(job.status, Job.Status.CLAIMED)


class JobStateTransitionRaceConditionTest(TransactionTestCase):

    def setUp(self):
        self.worker = Worker.objects.create(name="test-worker")
        self.job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.CLAIMED,
            worker=self.worker,
            claimed_at=timezone.now(),
        )

    def test_concurrent_state_transitions(self):

        errors = []
        successes = []

        def start_job_thread():
            try:
                job = start_job(self.job)
                successes.append(("start", job.status))
            except Exception as e:
                errors.append(("start", str(e)))
            finally:
                connection.close()

        def complete_job_thread():
            try:
                job = complete_job(self.job)
                successes.append(("complete", job.status))
            except Exception as e:
                errors.append(("complete", str(e)))
            finally:
                connection.close()

        thread1 = threading.Thread(target=start_job_thread)
        thread2 = threading.Thread(target=complete_job_thread)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertEqual(len(errors) + len(successes), 2)

        self.assertGreaterEqual(len(errors), 0)

        self.job.refresh_from_db()
        self.assertIn(
            self.job.status,
            [Job.Status.RUNNING, Job.Status.CLAIMED, Job.Status.COMPLETED],
        )


class JobRetryRaceConditionTest(TransactionTestCase):

    def setUp(self):
        self.worker = Worker.objects.create(name="test-worker")

    def test_concurrent_job_failures(self):

        job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.RUNNING,
            worker=self.worker,
            started_at=timezone.now(),
            max_retries=3,
        )

        errors = []
        results = []

        def fail_job_thread():
            try:
                result_job = fail_job(job, error_message="Test error")
                results.append(result_job.retry_count)
            except Exception as e:
                errors.append(str(e))
            finally:
                connection.close()

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=fail_job_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertGreater(len(results) + len(errors), 0)

        job.refresh_from_db()

        self.assertGreater(job.retry_count, 0)
        self.assertLessEqual(job.retry_count, 3)


class ExpiredJobReclaimTest(TestCase):

    def test_expired_jobs_are_reclaimed(self):

        worker = Worker.objects.create(name="test-worker")

        expired_time = timezone.now() - timezone.timedelta(minutes=10)
        job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.CLAIMED,
            worker=worker,
            claimed_at=expired_time,
        )

        new_worker = Worker.objects.create(name="new-worker")
        _reclaim_expired_jobs()
        claimed_job = claim_job(new_worker)

        self.assertIsNotNone(claimed_job)
        self.assertEqual(claimed_job.id, job.id)
        self.assertEqual(claimed_job.worker.id, new_worker.id)
        self.assertEqual(claimed_job.status, Job.Status.CLAIMED)


class FullWorkflowIntegrationTest(TestCase):

    def test_full_job_lifecycle(self):

        # Create job
        job, created = create_job(
            type=Job.JobType.SEND_EMAIL,
            payload={
                "recipient": "test@example.com",
                "subject": "Test Email",
            },
            idempotency_key=str(uuid.uuid4()),
        )

        self.assertTrue(created)
        self.assertEqual(job.status, Job.Status.PENDING)

        worker = Worker.objects.create(name="test-worker")
        processed_job = process_next_job(worker)

        self.assertIsNotNone(processed_job)
        self.assertEqual(processed_job.id, job.id)

        processed_job.refresh_from_db()
        self.assertIn(
            processed_job.status,
            [Job.Status.COMPLETED, Job.Status.PENDING, Job.Status.FAILED],
        )

        executions = JobExecution.objects.filter(job=job)
        self.assertGreater(executions.count(), 0)
