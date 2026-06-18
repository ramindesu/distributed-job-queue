from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from services.claim_job import claim_job
from serializers.job_detail import JobDetailSerializer


class ClaimJobView(APIView):
    def post(self, request):
        worker_id = request.data.get("worker_id")
        if not worker_id:
            return Response(
                {"detail": "worker_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        worker = get_object_or_404(worker, pk=worker_id)
        job = claim_job(worker)
        if not job:
            return Response(
                {"detail": "No pending jobs available"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(JobDetailSerializer(job).data)
