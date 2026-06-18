from rest_framework import serializers
from ..models.job_execution import JobExecution


class JobExecutionSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobExecution
        exclude = ["job"]  