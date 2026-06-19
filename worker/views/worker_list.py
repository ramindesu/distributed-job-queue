from django.urls import path
from rest_framework.generics import ListAPIView
from ..models import Worker
from ..serializers import WorkerSerializer

class WorkerListView(ListAPIView):
    queryset = Worker.objects.all().order_by('-last_heartbeat')
    serializer_class = WorkerSerializer