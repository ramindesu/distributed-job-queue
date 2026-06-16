from django.db import models
from django.utils import timezone
from datetime import timedelta


class Worker(models.Model):
    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"

    name = models.CharField(max_length=30, unique=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ONLINE, db_index=True
    )
    last_heartbeat = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_alive(self):
        return (
            self.status == self.Status.ONLINE
            and self.last_heartbeat >= timezone.now - timedelta(minutes=5)
        )

    def __str__(self):
        return f"worker {self.name} is {self.status}"

    class Meta:
        ordering = ["-created_at"]
