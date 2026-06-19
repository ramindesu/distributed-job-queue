import time
import signal
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from worker.models.worker import Worker
from job.services import process_next_job


class Command(BaseCommand):
    help = "Run a job queue worker"

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Worker name (default: worker-<timestamp>)",
        )
        parser.add_argument(
            "--poll-interval",
            type=int,
            default=5,
            help="Seconds to wait between polling for jobs (default: 5)",
        )

    def __init__(self):
        super().__init__()
        self.worker = None
        self.should_stop = False

    def handle(self, *args, **options):
        worker_name = options["name"] or f"worker-{int(time.time())}"
        poll_interval = options["poll_interval"]

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.worker, created = Worker.objects.get_or_create(
            name=worker_name,
            defaults={"status": Worker.Status.ONLINE},
        )

        if not created:

            self.worker.status = Worker.Status.ONLINE
            self.worker.last_heartbeat = timezone.now()
            self.worker.save(update_fields=["status", "last_heartbeat"])

        self.stdout.write(
            self.style.SUCCESS(f"Worker '{worker_name}' started successfully")
        )
        self.stdout.write(f"Polling for jobs every {poll_interval} seconds...")
        self.stdout.write("Press Ctrl+C to stop\n")

        jobs_processed = 0
        while not self.should_stop:
            try:

                self._update_heartbeat()

                job = process_next_job(self.worker)

                if job:
                    jobs_processed += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[{timezone.now().strftime('%H:%M:%S')}] "
                            f"Processed job #{job.id} ({job.type}) - "
                            f"Status: {job.status}"
                        )
                    )
                else:

                    self.stdout.write(
                        f"[{timezone.now().strftime('%H:%M:%S')}] "
                        f"No jobs available. Waiting..."
                    )

                time.sleep(poll_interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error in worker loop: {e}"))
                time.sleep(poll_interval)

        self._shutdown()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nWorker '{worker_name}' stopped. "
                f"Total jobs processed: {jobs_processed}"
            )
        )

    def _update_heartbeat(self):

        with transaction.atomic():
            worker = Worker.objects.select_for_update().get(pk=self.worker.pk)
            worker.last_heartbeat = timezone.now()
            worker.save(update_fields=["last_heartbeat"])

    def _signal_handler(self, signum, frame):

        self.stdout.write("\nReceived shutdown signal. Stopping worker...")
        self.should_stop = True

    def _shutdown(self):

        if self.worker:
            self.worker.status = Worker.Status.OFFLINE
            self.worker.save(update_fields=["status"])
