from rest_framework import serializers

from models.job import Job


class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "type",
            "payload",
            "idempotency_key",
        ]
