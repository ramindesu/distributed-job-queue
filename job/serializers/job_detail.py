from rest_framework import serializers
from worker.models.worker import Worker
from models.job import Job
from job_execution import JobExecutionSerializer

class WorkerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ["id", "name", "status"]


class JobDetailSerializer(serializers.ModelSerializer):
    worker = WorkerDetailSerializer(read_only=True)
    executions = JobExecutionSerializer(many=True,read_only=True)

    class Meta:
        model = Job
        fields = "__all__"
