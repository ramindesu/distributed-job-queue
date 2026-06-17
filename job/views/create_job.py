from rest_framework.generics import CreateAPIView

from models import Job
from serializers import JobCreateSerializer

class JobCreate(CreateAPIView):
    queryset = Job.objects.select_related("worker")
    serializer_class = JobCreateSerializer
