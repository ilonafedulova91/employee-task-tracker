from typing import Any

from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Task
from .permissions import IsManagerOrAssignedEmployee
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """Provide CRUD operations and filtering for employee tasks."""

    queryset = Task.objects.none()
    serializer_class = TaskSerializer
    permission_classes = [IsManagerOrAssignedEmployee]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "priority", "assignee"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "deadline", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self) -> QuerySet[Task]:
        """Return all tasks for managers and assigned tasks for employees."""
        if getattr(self, "swagger_fake_view", False):
            return Task.objects.none()

        user = self.request.user
        queryset = Task.objects.select_related("assignee", "created_by")

        if user.is_staff:
            return queryset.all()

        return queryset.filter(assignee=user)

    def create(
        self,
        request: Request,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        """Allow only managers to create tasks."""
        if not request.user.is_staff:
            raise PermissionDenied("Only managers can create tasks.")

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer: TaskSerializer) -> None:
        """Save the authenticated manager as the task creator."""
        serializer.save(created_by=self.request.user)
