from rest_framework.generics import CreateAPIView

from ..serializers import JobCreateSerializer


class JobCreate(CreateAPIView):
    serializer_class = JobCreateSerializer