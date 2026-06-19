from django.urls import path
from .views.worker_list import WorkerListView
urlpatterns = [
    path("",WorkerListView.as_view(), name="worker-list")
    
]
