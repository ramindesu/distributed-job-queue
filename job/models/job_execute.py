from django.db import models


class JobExecution(models.Model):

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    job = models.ForeignKey(
        "job.Job",
        on_delete=models.CASCADE,
        related_name="executions",
    )

    worker = models.ForeignKey(
        "workers.Worker",
        on_delete=models.SET_NULL,
        null=True,
        related_name="executions",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )

    started_at = models.DateTimeField()

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    result = models.JSONField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"Execution #{self.id} "
            f"for Job #{self.job_id} "
            f"({self.status})"
        )

    class Meta:
        ordering = ["-started_at"]