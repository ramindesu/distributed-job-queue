from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from ..serializers import JobCreateSerializer
from ..services import create_job


class JobCreate(CreateAPIView):
    serializer_class = JobCreateSerializer

    def perform_create(self, serializer):
        job, created = create_job(**serializer.validated_data)

        serializer.instance = job

        self._job_created = created

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_status = status.HTTP_201_CREATED if self._job_created else status.HTTP_200_OK
        return Response(serializer.data, status=response_status)