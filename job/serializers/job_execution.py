from rest_framework import serializers
from ..models.job_execute import JobExecution
class JobExecutionSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobExecution
        fields = "__all__"