from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from job.models.job import Job
from worker.models.worker import Worker
from job.services.process_next_job import _reclaim_stuck_jobs


class ExecutionTimeoutTest(TestCase):

    def setUp(self):
        self.worker = Worker.objects.create(name="test-worker")

    def test_job_within_timeout_not_reclaimed(self):

        job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.RUNNING,
            worker=self.worker,
            started_at=timezone.now() - timedelta(minutes=2),
            claimed_at=timezone.now() - timedelta(minutes=3),
        )

        _reclaim_stuck_jobs()

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.RUNNING)
        self.assertEqual(job.retry_count, 0)

    def test_job_exceeded_timeout_is_reclaimed(self):

        job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.RUNNING,
            worker=self.worker,
            started_at=timezone.now() - timedelta(minutes=10),
            claimed_at=timezone.now() - timedelta(minutes=11),
            max_retries=3,
        )

        # Run reclaim
        _reclaim_stuck_jobs()

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING)
        self.assertEqual(job.retry_count, 1)
        self.assertIsNone(job.worker)
        self.assertIsNone(job.started_at)

    def test_job_exceeded_timeout_max_retries_reached(self):

        job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.RUNNING,
            worker=self.worker,
            started_at=timezone.now() - timedelta(minutes=10),
            claimed_at=timezone.now() - timedelta(minutes=11),
            retry_count=2,  # Already retried twice
            max_retries=3,
        )

        _reclaim_stuck_jobs()

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.FAILED)
        self.assertEqual(job.retry_count, 3)
        self.assertIsNotNone(job.completed_at)

    def test_different_timeouts_per_job_type(self):

        email_job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={"recipient": "test@example.com"},
            status=Job.Status.RUNNING,
            worker=self.worker,
            started_at=timezone.now() - timedelta(minutes=7),
        )

        report_job = Job.objects.create(
            type=Job.JobType.GENERATE_REPORT,
            payload={"report_type": "monthly"},
            status=Job.Status.RUNNING,
            worker=self.worker,
            started_at=timezone.now() - timedelta(minutes=7),
        )

        _reclaim_stuck_jobs()

        email_job.refresh_from_db()
        self.assertEqual(email_job.status, Job.Status.PENDING)

        report_job.refresh_from_db()
        self.assertEqual(report_job.status, Job.Status.RUNNING)

    def test_execution_expired_property(self):

        job1 = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={},
            status=Job.Status.RUNNING,
            started_at=timezone.now() - timedelta(minutes=2),
        )
        self.assertFalse(job1.execution_expired)

        job2 = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={},
            status=Job.Status.RUNNING,
            started_at=timezone.now() - timedelta(minutes=10),
        )
        self.assertTrue(job2.execution_expired)

        job3 = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={},
            status=Job.Status.PENDING,
            started_at=None,
        )
        self.assertFalse(job3.execution_expired)

    def test_get_execution_timeout_minutes(self):

        email_job = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={},
        )
        self.assertEqual(email_job.get_execution_timeout_minutes(), 5)

        report_job = Job.objects.create(
            type=Job.JobType.GENERATE_REPORT,
            payload={},
        )
        self.assertEqual(report_job.get_execution_timeout_minutes(), 30)

        ticket_job = Job.objects.create(
            type=Job.JobType.RESERVE_TICKET,
            payload={},
        )
        self.assertEqual(ticket_job.get_execution_timeout_minutes(), 10)


class ClaimExpirationTest(TestCase):

    def setUp(self):
        self.worker = Worker.objects.create(name="test-worker")

    def test_claim_expired_property(self):

        from job.services.process_next_job import _reclaim_expired_jobs

        job1 = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={},
            status=Job.Status.CLAIMED,
            worker=self.worker,
            claimed_at=timezone.now() - timedelta(minutes=2),
        )
        self.assertFalse(job1.claim_expired)

        job2 = Job.objects.create(
            type=Job.JobType.SEND_EMAIL,
            payload={},
            status=Job.Status.CLAIMED,
            worker=self.worker,
            claimed_at=timezone.now() - timedelta(minutes=10),
        )
        self.assertTrue(job2.claim_expired)

        _reclaim_expired_jobs()

        job1.refresh_from_db()
        self.assertEqual(job1.status, Job.Status.CLAIMED)

        job2.refresh_from_db()
        self.assertEqual(job2.status, Job.Status.PENDING)
        self.assertIsNone(job2.worker)
