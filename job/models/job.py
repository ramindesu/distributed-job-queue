from django.db import models


class Job(models.Model):

    class JobType(models.TextChoices):
        SEND_EMAIL = "send_email", "Send Email"
        GENERATE_REPORT = "generate_report", "Generate Report"
        RESERVE_TICKET = "reserve_ticket", "Reserve Ticket"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLAIMED = "claimed", "Claimed"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    idempotency_key = models.UUIDField(
        unique=True,
        null=True,
        blank=True,
    )
    type = models.CharField(
        max_length=50,
        choices=JobType.choices,
        db_index=True
    )

    payload = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    worker = models.ForeignKey(
        "worker.Worker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )

    claimed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Job #{self.id} ({self.type}) - {self.status}"

    class Meta:
        ordering = ["id"]
