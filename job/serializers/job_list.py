from rest_framework import serializers
from ..models.job import Job


class JobListSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source="worker.name", read_only=True)

    class Meta:
        model = Job
        fields = ["id", "type", "status", "created_at", "worker_name"]
