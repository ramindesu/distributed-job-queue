from rest_framework.generics import RetrieveAPIView

from ..models import Job
from ..serializers import JobDetailSerializer


class JobDetailView(RetrieveAPIView):
    serializer_class = JobDetailSerializer
    queryset = Job.objects.select_related("worker").prefetch_related("executions")
