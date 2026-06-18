from django.urls import path
from .views import ClaimJobView, JobDetailView, JobCreateView

urlpatterns = [
    path("", JobCreateView.as_view(), name="job-create"),
    path("claim/", ClaimJobView.as_view(), name="job-claim",),
    path("detail/", JobDetailView.as_view(), name="job-detail"),
]

