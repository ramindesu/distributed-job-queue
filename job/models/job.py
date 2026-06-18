from django.db import models
from django.utils import timezone
from datetime import timedelta

class Job(models.Model):

    class JobType(models.TextChoices):
        SEND_EMAIL = "send_email", "Send Email"
        GENERATE_REPORT = "generate_report", "Generate Report"
        RESERVE_TICKET = "reserve_ticket", "Reserve Ticket"
    

    JOB_TYPE_TIMEOUTS = {
        JobType.SEND_EMAIL: 5,        
        JobType.GENERATE_REPORT: 30, 
        JobType.RESERVE_TICKET: 10,   
    }

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
    type = models.CharField(max_length=50, choices=JobType.choices, db_index=True)

    payload = models.JSONField()

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    worker = models.ForeignKey(
        "worker.Worker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        db_index=True
    )
    retry_count = models.PositiveIntegerField(default=0)

    max_retries = models.PositiveIntegerField(default=3)

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


    @property
    def claim_expired(self):
        if not self.claimed_at:
            return False

        return self.claimed_at < timezone.now() - timedelta(minutes=5)
    
    @property
    def execution_expired(self):
        """Check if job execution has exceeded timeout"""
        if not self.started_at or self.status != self.Status.RUNNING:
            return False
        
        timeout_minutes = self.JOB_TYPE_TIMEOUTS.get(self.type, 30)  # Default 30 min
        return self.started_at < timezone.now() - timedelta(minutes=timeout_minutes)
    
    def get_execution_timeout_minutes(self):
        """Get execution timeout for this job type"""
        return self.JOB_TYPE_TIMEOUTS.get(self.type, 30)

    def __str__(self):
        return f"Job #{self.id} ({self.type}) - {self.status}"

    class Meta:
        ordering = ["id"]
