from rest_framework.generics import ListAPIView
from ..models.job import Job
from ..serializers.job_list import JobListSerializer

class JobListView(ListAPIView):
    queryset = Job.objects.all().order_by('-created_at')[:20] 
    serializer_class = JobListSerializer