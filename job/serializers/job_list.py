from rest_framework import serializers
from ..models.job import Job

class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "type",
            "status",
            "created_at",
        ]