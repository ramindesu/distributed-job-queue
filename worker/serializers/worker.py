from rest_framework import serializers
from ..models.worker import Worker
class WorkerSerializer(serializers.ModelSerializer):
    is_alive =serializers.BooleanField(read_only=True)
    class Meta:
        model=Worker
        fields = ["id", "name", "status", "last_heartbeat", "created_at", "updated_at",'is_alive']
